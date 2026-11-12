from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.election import ElectionNotSetUpError
from dema.domain.run import Run
from dema.storage.elections import ElectionRecord, ElectionRepository
from dema.storage.runs import RunRepository
from dema.streaming.keys import ACTIVE_RUN_KEY


class ActiveRuns:
    def __init__(self, redis: Redis, connection: AsyncConnection) -> None:
        self._redis = redis
        self._runs = RunRepository(connection)
        self._elections = ElectionRepository(connection)
        self._records: dict[int, ElectionRecord] = {}

    @property
    def runs(self) -> RunRepository:
        return self._runs

    async def current_id(self) -> int:
        raw = await self._redis.get(ACTIVE_RUN_KEY)
        if raw is not None:
            return int(raw)
        run = await self._runs.active()
        if run is None:
            raise ElectionNotSetUpError
        await self._redis.set(ACTIVE_RUN_KEY, run.id)
        return run.id

    async def current(self) -> ElectionRecord:
        return await self.record(await self.current_id())

    async def record(self, run_id: int) -> ElectionRecord:
        if run_id not in self._records:
            run = await self._runs.get(run_id)
            self._records[run_id] = await self._elections.load(run)
        return self._records[run_id]

    async def family(self) -> tuple[ElectionRecord, ...]:
        current = await self.current()
        if current.run.parent_id is None:
            return (current,)
        return (await self.record(current.run.parent_id), current)

    async def activate(self, run_id: int) -> Run:
        run = await self._runs.activate(run_id)
        await self._redis.set(ACTIVE_RUN_KEY, run.id)
        self._records.pop(run_id, None)
        return run
