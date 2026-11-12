from dataclasses import dataclass
from datetime import datetime

from psycopg import AsyncConnection

from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionNotSetUpError
from dema.domain.run import Run
from dema.streaming.keys import ElectionKeys

POLLS_CLOSE = "SELECT polls_close FROM elections WHERE year = %s AND round = %s"

CANDIDATES = """
SELECT number, name, party, birth_date
FROM candidates
WHERE year = %s AND round = %s AND number = ANY(%s)
ORDER BY number
"""


@dataclass(frozen=True, slots=True)
class ElectionRecord:
    election: Election
    polls_close: datetime
    run: Run

    @property
    def keys(self) -> ElectionKeys:
        return ElectionKeys.for_run(self.run)


class ElectionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def load(self, run: Run) -> ElectionRecord:
        cursor = await self._connection.execute(POLLS_CLOSE, (run.year, run.round))
        row = await cursor.fetchone()
        if row is None:
            raise ElectionNotSetUpError
        cursor = await self._connection.execute(
            CANDIDATES, (run.year, run.round, list(run.candidates))
        )
        candidates = tuple(Candidate(*fields) for fields in await cursor.fetchall())
        return ElectionRecord(
            election=Election(year=run.year, round=run.round, candidates=candidates),
            polls_close=row[0],
            run=run,
        )
