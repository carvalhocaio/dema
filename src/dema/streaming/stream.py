from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from redis.typing import EncodableT, FieldT

from dema.integrity.signer import SignedBallot
from dema.streaming.keys import CONSUMER_GROUP, ElectionKeys

Fields = Mapping[bytes, bytes]
StreamMessages = list[tuple[bytes, list[tuple[bytes, Fields]]]]


@dataclass(frozen=True, slots=True)
class StreamEntry:
    id: bytes
    signed: SignedBallot | None


class BallotStream:
    def __init__(
        self, redis: Redis, keys: ElectionKeys, group: str = CONSUMER_GROUP
    ) -> None:
        self._redis = redis
        self._keys = keys
        self._group = group

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._keys.ballots, self._group, id="0", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def publish(self, ballots: Sequence[SignedBallot]) -> int:
        if not ballots:
            return 0
        async with self._redis.pipeline(transaction=False) as pipe:
            for ballot in ballots:
                pipe.xadd(
                    self._keys.ballots,
                    {"payload": ballot.payload, "signature": ballot.signature},
                )
            await pipe.execute()
        return len(ballots)

    async def read(self, consumer: str, count: int, block_ms: int) -> list[StreamEntry]:
        response = await self._redis.xreadgroup(
            self._group, consumer, {self._keys.ballots: ">"}, count, block_ms
        )
        return [
            _entry(entry_id, fields)
            for _, messages in cast(StreamMessages, response or [])
            for entry_id, fields in messages
        ]

    async def claim_stale(
        self, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntry]:
        _, messages, *_ = await self._redis.xautoclaim(
            self._keys.ballots, self._group, consumer, min_idle_ms, count=count
        )
        return [_entry(entry_id, fields) for entry_id, fields in messages if fields]

    async def acknowledge(self, entries: Sequence[StreamEntry]) -> None:
        if entries:
            await self._redis.xack(
                self._keys.ballots, self._group, *(entry.id for entry in entries)
            )

    async def reject(self, entry: StreamEntry, reason: str) -> None:
        fields: dict[FieldT, EncodableT] = {"entry": entry.id, "reason": reason}
        if entry.signed is not None:
            fields |= {
                "payload": entry.signed.payload,
                "signature": entry.signed.signature,
            }
        await self._redis.xadd(self._keys.rejected, fields)

    async def clear(self) -> None:
        await self._redis.delete(self._keys.ballots, self._keys.rejected)


def _entry(entry_id: bytes, fields: Fields) -> StreamEntry:
    payload = fields.get(b"payload")
    signature = fields.get(b"signature")
    if payload is None or signature is None:
        return StreamEntry(id=entry_id, signed=None)
    return StreamEntry(
        id=entry_id, signed=SignedBallot(payload=payload, signature=signature.decode())
    )
