from collections.abc import Callable
from typing import Protocol

from dema.api.schemas import ResultsView
from dema.domain.election import Election, ElectionRound
from dema.storage.elections import ElectionRecord
from dema.tallying.outcome import decide
from dema.tallying.tally import Tally


class SnapshotSource(Protocol):
    async def snapshot(self) -> Tally: ...


class ElectionSource(Protocol):
    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord: ...


SnapshotFactory = Callable[[Election], SnapshotSource]


class ActiveRound:
    def __init__(
        self,
        elections: ElectionSource,
        snapshots: SnapshotFactory,
        year: int,
        round_: ElectionRound,
    ) -> None:
        self._elections = elections
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
            record = await self._elections.load(self._year, self._round)
            self._election = record.election
            self._source = self._snapshots(record.election)
        return self._election, self._source
