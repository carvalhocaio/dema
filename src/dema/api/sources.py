from collections.abc import Callable
from typing import Protocol

from psycopg import AsyncConnection

from dema.api.schemas import ResultsView
from dema.domain.election import Election, ElectionRound
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.elections import ElectionRecord, ElectionRepository
from dema.tallying.outcome import decide
from dema.tallying.states import StateTally
from dema.tallying.tally import Tally
from dema.tallying.timeline import Timeline


class SnapshotSource(Protocol):
    async def snapshot(self) -> Tally: ...


SnapshotFactory = Callable[[Election], SnapshotSource]


class Archive(Protocol):
    async def rounds(self, year: int) -> list[ElectionRound]: ...

    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord: ...

    async def tally(self, election: Election) -> Tally: ...

    async def timeline(self, election: Election) -> Timeline: ...

    async def states(self, election: Election) -> tuple[StateTally, ...]: ...


class PostgresArchive:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self._elections = ElectionRepository(connection)

    async def rounds(self, year: int) -> list[ElectionRound]:
        return await self._elections.rounds(year)

    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord:
        return await self._elections.load(year, round_)

    async def tally(self, election: Election) -> Tally:
        return await PostgresBallotRepository(self._connection, election).tally()

    async def timeline(self, election: Election) -> Timeline:
        return await PostgresBallotRepository(self._connection, election).timeline()

    async def states(self, election: Election) -> tuple[StateTally, ...]:
        return await PostgresBallotRepository(self._connection, election).states()


class ActiveRound:
    def __init__(
        self,
        archive: Archive,
        snapshots: SnapshotFactory,
        year: int,
        round_: ElectionRound,
    ) -> None:
        self._archive = archive
        self._snapshots = snapshots
        self._year = year
        self._round = round_
        self._election: Election | None = None
        self._source: SnapshotSource | None = None

    async def results(self) -> ResultsView:
        election, source = await self._resolve()
        tally = await source.snapshot()
        return ResultsView.build(election, tally, decide(election, tally))

    async def _resolve(self) -> tuple[Election, SnapshotSource]:
        if self._election is None or self._source is None:
            record = await self._archive.load(self._year, self._round)
            self._election = record.election
            self._source = self._snapshots(record.election)
        return self._election, self._source
