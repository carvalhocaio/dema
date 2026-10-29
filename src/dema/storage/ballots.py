from collections.abc import Sequence

from psycopg import AsyncConnection

from dema.domain.election import Election
from dema.integrity.signer import VerifiedBallot
from dema.tallying.tally import Tally

INSERT_BALLOTS = """
INSERT INTO ballots
    (year, round, section, blank_votes, null_votes, issued_at, payload, signature)
SELECT %(year)s, %(round)s, *
FROM unnest(
    %(sections)s::text[], %(blank)s::int[], %(null)s::int[],
    %(issued_at)s::timestamptz[], %(payloads)s::bytea[], %(signatures)s::text[]
)
ON CONFLICT DO NOTHING
RETURNING section
"""

INSERT_VOTES = """
INSERT INTO ballot_votes (year, round, section, candidate, votes)
SELECT %(year)s, %(round)s, *
FROM unnest(%(sections)s::text[], %(candidates)s::smallint[], %(votes)s::int[])
"""

TOTALS = """
SELECT
    (SELECT count(*) FROM sections),
    (SELECT coalesce(sum(eligible_voters), 0) FROM sections),
    count(b.section),
    coalesce(sum(s.eligible_voters), 0),
    coalesce(sum(b.blank_votes), 0),
    coalesce(sum(b.null_votes), 0)
FROM ballots AS b
JOIN sections AS s ON s.key = b.section
WHERE b.year = %(year)s AND b.round = %(round)s
"""

VOTES = """
SELECT candidate, sum(votes)
FROM ballot_votes
WHERE year = %(year)s AND round = %(round)s
GROUP BY candidate
"""

COUNTED_SECTIONS = (
    "SELECT section FROM ballots WHERE year = %(year)s AND round = %(round)s"
)


class PostgresBallotRepository:
    def __init__(self, connection: AsyncConnection, election: Election) -> None:
        self._connection = connection
        self._election = election

    async def save_many(self, verified: Sequence[VerifiedBallot]) -> int:
        unique = _by_section(verified)
        if not unique:
            return 0
        async with self._connection.transaction():
            cursor = await self._connection.execute(
                INSERT_BALLOTS, self._scope() | _ballot_columns(list(unique.values()))
            )
            inserted = {section for (section,) in await cursor.fetchall()}
            fresh = [unique[section] for section in inserted]
            if fresh:
                await self._connection.execute(
                    INSERT_VOTES, self._scope() | _vote_columns(fresh)
                )
        return len(inserted)

    async def tally(self) -> Tally:
        cursor = await self._connection.execute(TOTALS, self._scope())
        [
            (sections, electorate, counted, counted_electorate, blank, null)
        ] = await cursor.fetchall()
        cursor = await self._connection.execute(VOTES, self._scope())
        votes = dict.fromkeys(self._election.candidate_numbers, 0)
        votes |= {candidate: int(total) for candidate, total in await cursor.fetchall()}
        return Tally(
            nominal_votes=votes,
            blank_votes=int(blank),
            null_votes=int(null),
            counted_sections=counted,
            counted_electorate=int(counted_electorate),
            total_sections=sections,
            total_electorate=int(electorate),
        )

    async def counted_sections(self) -> list[str]:
        cursor = await self._connection.execute(COUNTED_SECTIONS, self._scope())
        return [section for (section,) in await cursor.fetchall()]

    def _scope(self) -> dict[str, int]:
        return {"year": self._election.year, "round": self._election.round}


def _by_section(verified: Sequence[VerifiedBallot]) -> dict[str, VerifiedBallot]:
    unique: dict[str, VerifiedBallot] = {}
    for item in verified:
        unique.setdefault(str(item.ballot.section), item)
    return unique


def _ballot_columns(verified: Sequence[VerifiedBallot]) -> dict[str, list]:
    return {
        "sections": [str(v.ballot.section) for v in verified],
        "blank": [v.ballot.blank_votes for v in verified],
        "null": [v.ballot.null_votes for v in verified],
        "issued_at": [v.ballot.issued_at for v in verified],
        "payloads": [v.signed.payload for v in verified],
        "signatures": [v.signed.signature for v in verified],
    }


def _vote_columns(verified: Sequence[VerifiedBallot]) -> dict[str, list]:
    rows = [
        (str(v.ballot.section), number, votes)
        for v in verified
        for number, votes in v.ballot.nominal_votes.items()
    ]
    sections, candidates, votes = (list(column) for column in zip(*rows, strict=True))
    return {"sections": sections, "candidates": candidates, "votes": votes}
