from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from psycopg import AsyncConnection

from dema.domain.election import Election
from dema.integrity.signer import VerifiedBallot
from dema.tallying.tally import Tally
from dema.tallying.timeline import MinuteCount, Timeline, build_timeline

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

ROLLUP_TOTALS = """
INSERT INTO minute_totals
    (year, round, minute, sections, electorate, blank_votes, null_votes)
SELECT
    b.year, b.round, date_trunc('minute', b.issued_at, 'UTC') AS minute,
    count(*), sum(s.eligible_voters), sum(b.blank_votes), sum(b.null_votes)
FROM ballots AS b
JOIN sections AS s ON s.key = b.section
WHERE b.year = %(year)s AND b.round = %(round)s {sections}
GROUP BY b.year, b.round, minute
ORDER BY minute
ON CONFLICT (year, round, minute) DO UPDATE SET
    sections = minute_totals.sections + EXCLUDED.sections,
    electorate = minute_totals.electorate + EXCLUDED.electorate,
    blank_votes = minute_totals.blank_votes + EXCLUDED.blank_votes,
    null_votes = minute_totals.null_votes + EXCLUDED.null_votes
"""

ROLLUP_VOTES = """
INSERT INTO minute_votes (year, round, minute, candidate, votes)
SELECT
    v.year, v.round, date_trunc('minute', b.issued_at, 'UTC') AS minute,
    v.candidate, sum(v.votes)
FROM ballot_votes AS v
JOIN ballots AS b USING (year, round, section)
WHERE v.year = %(year)s AND v.round = %(round)s {sections}
GROUP BY v.year, v.round, minute, v.candidate
ORDER BY minute, v.candidate
ON CONFLICT (year, round, minute, candidate) DO UPDATE SET
    votes = minute_votes.votes + EXCLUDED.votes
"""

ONLY_SECTIONS = "AND b.section = ANY(%(sections)s::text[])"

CLEAR_ROLLUP = (
    "DELETE FROM minute_votes WHERE year = %(year)s AND round = %(round)s",
    "DELETE FROM minute_totals WHERE year = %(year)s AND round = %(round)s",
)

MINUTE_TOTALS = """
SELECT minute, sections, electorate, blank_votes, null_votes
FROM minute_totals
WHERE year = %(year)s AND round = %(round)s
"""

MINUTE_VOTES = """
SELECT minute, candidate, votes
FROM minute_votes
WHERE year = %(year)s AND round = %(round)s
"""

TOTALS_ONLY = "SELECT count(*), coalesce(sum(eligible_voters), 0) FROM sections"


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
            inserted = sorted(section for (section,) in await cursor.fetchall())
            if inserted:
                fresh = [unique[section] for section in inserted]
                await self._connection.execute(
                    INSERT_VOTES, self._scope() | _vote_columns(fresh)
                )
                await self._roll_up(ONLY_SECTIONS, {"sections": inserted})
        return len(inserted)

    async def rebuild_rollup(self) -> None:
        async with self._connection.transaction():
            for statement in CLEAR_ROLLUP:
                await self._connection.execute(statement, self._scope())
            await self._roll_up("", {})

    async def timeline(self) -> Timeline:
        cursor = await self._connection.execute(TOTALS_ONLY)
        [(sections, electorate)] = await cursor.fetchall()
        cursor = await self._connection.execute(MINUTE_VOTES, self._scope())
        votes: dict[datetime, dict[int, int]] = defaultdict(dict)
        for minute, candidate, total in await cursor.fetchall():
            votes[minute][candidate] = int(total)
        cursor = await self._connection.execute(MINUTE_TOTALS, self._scope())
        minutes = [
            MinuteCount(
                minute=minute,
                sections=counted,
                electorate=int(counted_electorate),
                blank_votes=int(blank),
                null_votes=int(null),
                nominal_votes=votes[minute],
            )
            for minute, counted, counted_electorate, blank, null in (
                await cursor.fetchall()
            )
        ]
        return build_timeline(self._election, minutes, sections, int(electorate))

    async def _roll_up(self, sections: str, params: dict[str, list[str]]) -> None:
        for template in (ROLLUP_TOTALS, ROLLUP_VOTES):
            await self._connection.execute(
                template.format(sections=sections).encode(), self._scope() | params
            )

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
    return dict(sorted(unique.items()))


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
