from collections.abc import Callable
from typing import Protocol

from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.api.schemas import ResultsView
from dema.director.control import ControlStream, CountRequest
from dema.domain.run import Run
from dema.runtime.active import ActiveRuns
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.elections import ElectionRecord
from dema.tallying.outcome import decide
from dema.tallying.states import StateTally
from dema.tallying.tally import Tally
from dema.tallying.timeline import Timeline


class SnapshotSource(Protocol):
    async def snapshot(self) -> Tally: ...


SnapshotFactory = Callable[[ElectionRecord], SnapshotSource]


class Archive(Protocol):
    async def family(self) -> tuple[ElectionRecord, ...]: ...

    async def current_run(self) -> Run | None: ...

    async def request_run(self, seed: int, speed: float | None) -> Run: ...

    async def tally(self, record: ElectionRecord) -> Tally: ...

    async def timeline(self, record: ElectionRecord) -> Timeline: ...

    async def states(self, record: ElectionRecord) -> tuple[StateTally, ...]: ...


class PostgresArchive:
    def __init__(self, connection: AsyncConnection, redis: Redis, year: int) -> None:
        self._connection = connection
        self._active = ActiveRuns(redis, connection)
        self._control = ControlStream(redis)
        self._year = year

    async def family(self) -> tuple[ElectionRecord, ...]:
        return await self._active.family()

    async def current_run(self) -> Run | None:
        return await self._active.runs.active()

    async def request_run(self, seed: int, speed: float | None) -> Run:
        run = await self._active.runs.create_first_round(self._year, seed)
        await self._control.request(CountRequest(run_id=run.id, speed=speed))
        return run

    async def tally(self, record: ElectionRecord) -> Tally:
        return await self._repository(record).tally()

    async def timeline(self, record: ElectionRecord) -> Timeline:
        return await self._repository(record).timeline()

    async def states(self, record: ElectionRecord) -> tuple[StateTally, ...]:
        return await self._repository(record).states()

    def _repository(self, record: ElectionRecord) -> PostgresBallotRepository:
        return PostgresBallotRepository(
            self._connection, record.election, record.run.id
        )


class ActiveRound:
    def __init__(self, archive: Archive, snapshots: SnapshotFactory) -> None:
        self._archive = archive
        self._snapshots = snapshots
        self._sources: dict[int, SnapshotSource] = {}

    async def results(self) -> ResultsView:
        record = (await self._archive.family())[-1]
        source = self._sources.get(record.run.id)
        if source is None:
            source = self._sources[record.run.id] = self._snapshots(record)
        tally = await source.snapshot()
        election = record.election
        return ResultsView.build(election, tally, decide(election, tally), record.run)
