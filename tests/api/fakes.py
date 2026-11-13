from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from dema.domain.election import Election, ElectionNotSetUpError, ElectionRound
from dema.domain.run import Run, RunStatus
from dema.domain.state import State
from dema.monitoring.pipeline import ConsumerState, PipelineSnapshot, StreamStats
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.elections import ElectionRecord
from dema.tallying.states import (
    StateCount,
    StateTally,
    StateTotals,
    build_state_tallies,
)
from dema.tallying.tally import Tally
from dema.tallying.timeline import MinuteCount, Timeline, build_timeline
from tests.factories import make_run

FIRST_ROUND = DEMA_2026_FIRST_ROUND.election
SECOND_ROUND = Election(year=2026, round=ElectionRound.SECOND, candidates=(KEONS, NICO))
FIRST_RUN = make_run(1, candidates=tuple(sorted(FIRST_ROUND.candidate_numbers)))
SECOND_RUN = make_run(
    2, ElectionRound.SECOND, candidates=(KEONS.number, NICO.number), parent_id=1
)
FIRST_RECORD = ElectionRecord(FIRST_ROUND, DEMA_2026_FIRST_ROUND.polls_close, FIRST_RUN)
SECOND_RECORD = ElectionRecord(SECOND_ROUND, SECOND_ROUND_POLLS_CLOSE, SECOND_RUN)


def first_round_record(run_id: int, seed: int = 40) -> ElectionRecord:
    run = replace(FIRST_RUN, id=run_id, seed=seed)
    return replace(FIRST_RECORD, run=run)


def make_tally(
    counted_sections: int,
    keons: int = 600,
    nico: int = 400,
    election: Election = FIRST_ROUND,
) -> Tally:
    votes = dict.fromkeys(election.candidate_numbers, 0)
    votes |= {KEONS.number: keons, NICO.number: nico}
    return Tally(
        nominal_votes=votes,
        blank_votes=20,
        null_votes=30,
        counted_sections=counted_sections,
        counted_electorate=counted_sections * 300,
        total_sections=10,
        total_electorate=3_000,
    )


def make_timeline(election: Election) -> Timeline:
    start = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)
    minutes = [
        MinuteCount(
            minute=start + timedelta(minutes=offset),
            sections=5,
            electorate=1_500,
            blank_votes=10,
            null_votes=15,
            nominal_votes={KEONS.number: keons, NICO.number: 1_000 - keons},
        )
        for offset, keons in ((0, 400), (3, 900))
    ]
    return build_timeline(election, minutes, 10, 3_000)


def make_states(election: Election) -> tuple[StateTally, ...]:
    totals = [StateTotals(State.SP, 10, 3_000), StateTotals(State.ZZ, 2, 100)]
    counts = [
        StateCount(State.SP, 4, 1_200, 10, 15, {KEONS.number: 500, NICO.number: 400})
    ]
    return build_state_tallies(election, totals, counts)


class FakeSource:
    def __init__(self, tally: Tally | None = None) -> None:
        self.tally = tally

    async def snapshot(self) -> Tally:
        if self.tally is None:
            raise ElectionNotSetUpError
        return self.tally


class FakeArchive:
    def __init__(
        self,
        family: tuple[ElectionRecord, ...] = (FIRST_RECORD,),
        tallies: Mapping[ElectionRound, Tally] | None = None,
    ) -> None:
        self.records = family
        self.tallies = dict(tallies or {})
        self.requests: list[tuple[int, float | None]] = []

    async def family(self) -> tuple[ElectionRecord, ...]:
        if not self.records:
            raise ElectionNotSetUpError
        return self.records

    async def current_run(self) -> Run | None:
        return self.records[-1].run if self.records else None

    async def request_run(self, seed: int, speed: float | None) -> Run:
        if not self.records:
            raise ElectionNotSetUpError
        self.requests.append((seed, speed))
        return replace(FIRST_RUN, id=99, seed=seed, status=RunStatus.PREPARING)

    async def tally(self, record: ElectionRecord) -> Tally:
        return self.tallies[record.election.round]

    async def states(self, record: ElectionRecord) -> tuple[StateTally, ...]:
        return make_states(record.election)

    async def timeline(self, record: ElectionRecord) -> Timeline:
        return make_timeline(record.election)


def make_pipeline(counted: int = 4) -> PipelineSnapshot:
    stats = StreamStats(
        length=12,
        pending=3,
        lag=5,
        consumers=(ConsumerState("demo-0-0", 3, 120), ConsumerState("old", 0, 9_000)),
        rejected=1,
        counted=counted,
    )
    return PipelineSnapshot(
        run=FIRST_RUN, stats=stats, rate=12.345, peak_rate=40.0, rates=(0.0, 12.345)
    )


class FakePipeline:
    def __init__(self, snapshot: PipelineSnapshot | None = None) -> None:
        self.snapshot = snapshot

    async def collect(self) -> PipelineSnapshot:
        if self.snapshot is None:
            raise ElectionNotSetUpError
        return self.snapshot
