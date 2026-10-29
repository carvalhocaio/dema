from collections.abc import Iterable, Sequence
from itertools import batched

from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.domain.election import Election
from dema.streaming.keys import ElectionKeys
from dema.tallying.tally import Tally
from dema.tallying.validation import ensure_known_candidates

ADD_BALLOT = """
if redis.call('SADD', KEYS[1], ARGV[1]) == 0 then
    return 0
end
redis.call('HINCRBY', KEYS[2], 'electorate', ARGV[2])
redis.call('HINCRBY', KEYS[2], 'blank', ARGV[3])
redis.call('HINCRBY', KEYS[2], 'null', ARGV[4])
for i = 5, #ARGV, 2 do
    redis.call('HINCRBY', KEYS[2], 'candidate:' .. ARGV[i], ARGV[i + 1])
end
return 1
"""
RESTORE_CHUNK = 10_000


class ElectionNotSetUpError(RuntimeError):
    pass


class RedisTallyStore:
    def __init__(self, redis: Redis, keys: ElectionKeys, election: Election) -> None:
        self._redis = redis
        self._keys = keys
        self._election = election
        self._add_ballot = redis.register_script(ADD_BALLOT)

    async def reset(self, total_sections: int, total_electorate: int) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(self._keys.counted, self._keys.tally, self._keys.meta)
            pipe.hset(
                self._keys.meta,
                mapping={
                    "total_sections": total_sections,
                    "total_electorate": total_electorate,
                },
            )
            await pipe.execute()

    async def add_many(self, ballots: Sequence[Ballot]) -> int:
        for ballot in ballots:
            ensure_known_candidates(self._election, ballot)
        async with self._redis.pipeline(transaction=False) as pipe:
            for ballot in ballots:
                await self._add_ballot(
                    keys=[self._keys.counted, self._keys.tally],
                    args=_ballot_args(ballot),
                    client=pipe,
                )
            results = await pipe.execute()
        return sum(results)

    async def restore(self, tally: Tally, sections: Iterable[str]) -> None:
        await self.reset(tally.total_sections, tally.total_electorate)
        for chunk in batched(sections, RESTORE_CHUNK):
            await self._redis.sadd(self._keys.counted, *chunk)
        await self._redis.hset(
            self._keys.tally,
            mapping={
                "electorate": tally.counted_electorate,
                "blank": tally.blank_votes,
                "null": tally.null_votes,
                **{f"candidate:{n}": v for n, v in tally.nominal_votes.items()},
            },
        )

    async def snapshot(self) -> Tally:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hgetall(self._keys.tally)
            pipe.scard(self._keys.counted)
            pipe.hgetall(self._keys.meta)
            fields, counted, meta = await pipe.execute()
        if not meta:
            raise ElectionNotSetUpError("run `dema election setup` first")
        totals = {key.decode(): int(value) for key, value in fields.items()}
        return Tally(
            nominal_votes={
                number: totals.get(f"candidate:{number}", 0)
                for number in self._election.candidate_numbers
            },
            blank_votes=totals.get("blank", 0),
            null_votes=totals.get("null", 0),
            counted_sections=counted,
            counted_electorate=totals.get("electorate", 0),
            total_sections=int(meta[b"total_sections"]),
            total_electorate=int(meta[b"total_electorate"]),
        )


def _ballot_args(ballot: Ballot) -> list[str | int]:
    args: list[str | int] = [
        str(ballot.section),
        ballot.eligible_voters,
        ballot.blank_votes,
        ballot.null_votes,
    ]
    for number, votes in ballot.nominal_votes.items():
        args += [number, votes]
    return args
