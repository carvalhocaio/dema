from collections.abc import Sequence
from typing import Any, cast

from psycopg import AsyncConnection

from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.domain.run import Run, RunStatus

Row = tuple[Any, ...]

COLUMNS = (
    "id, year, round, seed, status, candidates, parent_id, started_at, finished_at"
)

CREATE = f"""
INSERT INTO runs (year, round, seed, status, candidates, parent_id)
VALUES (%(year)s, %(round)s, %(seed)s, 'preparing', %(candidates)s, %(parent)s)
RETURNING {COLUMNS}
"""

CREATE_FIRST_ROUND = f"""
INSERT INTO runs (year, round, seed, status, candidates)
SELECT %(year)s, 1, %(seed)s, 'preparing', array_agg(number ORDER BY number)
FROM candidates
WHERE year = %(year)s AND round = 1
HAVING count(*) > 0
RETURNING {COLUMNS}
"""

GET = f"SELECT {COLUMNS} FROM runs WHERE id = %s"

ACTIVE = f"SELECT {COLUMNS} FROM runs WHERE id = (SELECT run_id FROM active_run)"

SUPERSEDE_ACTIVE = """
UPDATE runs SET status = 'superseded', finished_at = now()
WHERE id = (SELECT run_id FROM active_run)
    AND id <> %(run)s
    AND status IN ('preparing', 'counting')
"""

POINT = """
INSERT INTO active_run (run_id) VALUES (%(run)s)
ON CONFLICT (singleton) DO UPDATE SET run_id = EXCLUDED.run_id
"""

START = "UPDATE runs SET status = 'counting' WHERE id = %(run)s"

FINISH = """
UPDATE runs SET status = %(status)s, finished_at = now()
WHERE id = %(run)s AND status IN ('preparing', 'counting')
"""


class RunRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(
        self,
        year: int,
        round_: ElectionRound,
        seed: int,
        candidates: Sequence[int],
        parent_id: int | None = None,
    ) -> Run:
        cursor = await self._connection.execute(
            CREATE,
            {
                "year": year,
                "round": round_,
                "seed": seed,
                "candidates": sorted(candidates),
                "parent": parent_id,
            },
        )
        return _run(cast(Row, await cursor.fetchone()))

    async def create_first_round(self, year: int, seed: int) -> Run:
        cursor = await self._connection.execute(
            CREATE_FIRST_ROUND, {"year": year, "seed": seed}
        )
        row = await cursor.fetchone()
        if row is None:
            raise ElectionNotSetUpError
        return _run(row)

    async def get(self, run_id: int) -> Run:
        cursor = await self._connection.execute(GET, (run_id,))
        row = await cursor.fetchone()
        if row is None:
            raise ElectionNotSetUpError
        return _run(row)

    async def active(self) -> Run | None:
        cursor = await self._connection.execute(ACTIVE)
        row = await cursor.fetchone()
        return None if row is None else _run(row)

    async def activate(self, run_id: int) -> Run:
        params = {"run": run_id}
        async with self._connection.transaction():
            await self._connection.execute(SUPERSEDE_ACTIVE, params)
            await self._connection.execute(POINT, params)
            await self._connection.execute(START, params)
        return await self.get(run_id)

    async def finish(self, run_id: int, status: RunStatus) -> None:
        await self._connection.execute(FINISH, {"run": run_id, "status": status})


def _run(row: Row) -> Run:
    run_id, year, round_, seed, status, candidates, parent, started, finished = row
    return Run(
        id=run_id,
        year=year,
        round=ElectionRound(round_),
        seed=seed,
        status=RunStatus(status),
        candidates=tuple(candidates),
        parent_id=parent,
        started_at=started,
        finished_at=finished,
    )
