from dataclasses import dataclass
from datetime import datetime

from psycopg import AsyncConnection

from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionNotSetUpError, ElectionRound
from dema.streaming.keys import ElectionKeys

POLLS_CLOSE = "SELECT polls_close FROM elections WHERE year = %s AND round = %s"

CANDIDATES = """
SELECT number, name, party, birth_date
FROM candidates
WHERE year = %s AND round = %s
ORDER BY number
"""

ROUNDS = "SELECT round FROM elections WHERE year = %s ORDER BY round"


@dataclass(frozen=True, slots=True)
class ElectionRecord:
    election: Election
    polls_close: datetime

    @property
    def keys(self) -> ElectionKeys:
        return ElectionKeys.for_election(self.election)


class ElectionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord:
        cursor = await self._connection.execute(POLLS_CLOSE, (year, round_))
        row = await cursor.fetchone()
        if row is None:
            raise ElectionNotSetUpError
        cursor = await self._connection.execute(CANDIDATES, (year, round_))
        candidates = tuple(Candidate(*fields) for fields in await cursor.fetchall())
        return ElectionRecord(
            election=Election(year=year, round=round_, candidates=candidates),
            polls_close=row[0],
        )

    async def rounds(self, year: int) -> list[ElectionRound]:
        cursor = await self._connection.execute(ROUNDS, (year,))
        return [ElectionRound(round_) for (round_,) in await cursor.fetchall()]
