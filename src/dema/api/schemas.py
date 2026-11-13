from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dema.audit.ballots import AuditedBallot, Rejection
from dema.domain.election import Election
from dema.domain.run import Run, RunStatus
from dema.domain.state import Region
from dema.monitoring.pipeline import PipelineSnapshot
from dema.tallying.outcome import Margin, Outcome, Verdict, decide
from dema.tallying.states import StateTally
from dema.tallying.tally import Tally
from dema.tallying.timeline import Timeline

MAX_SEED = 2**62
RATE_DIGITS = 1


class View(BaseModel):
    model_config = ConfigDict(frozen=True)


class CandidateView(View):
    number: int
    name: str
    party: str
    votes: int
    share: float


class ProgressView(View):
    counted_sections: int
    total_sections: int
    counted_electorate: int
    total_electorate: int
    ratio: float
    is_complete: bool


class VotesView(View):
    valid: int
    blank: int
    null: int
    turnout: int
    abstentions: int


class MarginView(View):
    remaining_electorate: int
    leader: int
    leader_votes: int
    votes_to_majority: int
    runoff_gap: int | None

    @classmethod
    def build(cls, outcome: Outcome) -> "MarginView":
        margin: Margin = outcome.margin
        return cls(
            remaining_electorate=margin.remaining_electorate,
            leader=outcome.leader.candidate.number,
            leader_votes=margin.leader_votes,
            votes_to_majority=margin.votes_to_majority,
            runoff_gap=margin.runoff_gap,
        )


class RunView(View):
    id: int
    round: int
    seed: int
    status: RunStatus

    @classmethod
    def of(cls, run: Run) -> "RunView":
        return cls(id=run.id, round=run.round, seed=run.seed, status=run.status)


class RunRefView(View):
    id: int
    round: int
    seed: int

    @classmethod
    def of(cls, run: Run) -> "RunRefView":
        return cls(id=run.id, round=run.round, seed=run.seed)


class CurrentRunView(View):
    run: RunView | None
    runs_enabled: bool


class RunRequest(BaseModel):
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED)
    speed: float | None = Field(default=None, gt=0)


class ResultsView(View):
    year: int
    round: int
    progress: ProgressView
    votes: VotesView
    candidates: tuple[CandidateView, ...]
    verdict: Verdict
    finalists: tuple[int, ...]
    margin: MarginView
    run: RunRefView | None = None

    @classmethod
    def build(
        cls,
        election: Election,
        tally: Tally,
        outcome: Outcome,
        run: Run | None = None,
    ) -> "ResultsView":
        return cls(
            run=None if run is None else RunRefView.of(run),
            year=election.year,
            round=election.round,
            progress=ProgressView(
                counted_sections=tally.counted_sections,
                total_sections=tally.total_sections,
                counted_electorate=tally.counted_electorate,
                total_electorate=tally.total_electorate,
                ratio=tally.progress,
                is_complete=tally.is_complete,
            ),
            votes=VotesView(
                valid=tally.valid_votes,
                blank=tally.blank_votes,
                null=tally.null_votes,
                turnout=tally.turnout,
                abstentions=tally.abstentions,
            ),
            candidates=tuple(
                CandidateView(
                    number=result.candidate.number,
                    name=result.candidate.name,
                    party=result.candidate.party,
                    votes=result.votes,
                    share=result.share,
                )
                for result in outcome.ranking
            ),
            verdict=outcome.verdict,
            finalists=tuple(candidate.number for candidate in outcome.finalists),
            margin=MarginView.build(outcome),
        )


class RoundStatus(StrEnum):
    LIVE = "live"
    FINAL = "final"


class RoundView(View):
    round: int
    status: RoundStatus


class TimelinePointView(View):
    at: datetime
    progress: float
    shares: dict[int, float]
    verdict: Verdict


class TimelineView(View):
    year: int
    round: int
    points: tuple[TimelinePointView, ...]
    decided_at: datetime | None
    lead_changes: tuple[datetime, ...]

    @classmethod
    def build(cls, election: Election, timeline: Timeline) -> "TimelineView":
        return cls(
            year=election.year,
            round=election.round,
            points=tuple(
                TimelinePointView(
                    at=point.at,
                    progress=point.tally.progress,
                    shares={
                        number: point.tally.share(number)
                        for number in sorted(election.candidate_numbers)
                    },
                    verdict=point.outcome.verdict,
                )
                for point in timeline.points
            ),
            decided_at=timeline.decided_at,
            lead_changes=timeline.lead_changes,
        )


class ReplayPointView(View):
    at: datetime
    results: ResultsView


class ReplayView(View):
    year: int
    round: int
    points: tuple[ReplayPointView, ...]

    @classmethod
    def build(cls, election: Election, timeline: Timeline) -> "ReplayView":
        return cls(
            year=election.year,
            round=election.round,
            points=tuple(
                ReplayPointView(
                    at=point.at,
                    results=ResultsView.build(election, point.tally, point.outcome),
                )
                for point in timeline.points
            ),
        )


class StateCandidateView(View):
    number: int
    votes: int
    share: float


class StateView(View):
    state: str
    region: Region
    counted_sections: int
    total_sections: int
    progress: float
    candidates: tuple[StateCandidateView, ...]
    leader: int | None


class StatesView(View):
    year: int
    round: int
    states: tuple[StateView, ...]

    @classmethod
    def build(cls, election: Election, states: tuple[StateTally, ...]) -> "StatesView":
        return cls(
            year=election.year,
            round=election.round,
            states=tuple(
                StateView(
                    state=item.state.value,
                    region=item.state.region,
                    counted_sections=item.tally.counted_sections,
                    total_sections=item.tally.total_sections,
                    progress=item.tally.progress,
                    candidates=tuple(
                        StateCandidateView(
                            number=result.candidate.number,
                            votes=result.votes,
                            share=result.share,
                        )
                        for result in decide(election, item.tally).ranking
                    ),
                    leader=item.leader,
                )
                for item in states
            ),
        )


class ConsumerView(View):
    name: str
    pending: int
    idle_ms: int
    active: bool


class PipelineView(View):
    run: RunRefView
    stream_length: int
    pending: int
    lag: int | None
    consumers: tuple[ConsumerView, ...]
    rejected: int
    counted_sections: int
    rate: float
    peak_rate: float
    rates: tuple[float, ...]

    @classmethod
    def of(cls, snapshot: PipelineSnapshot) -> "PipelineView":
        stats = snapshot.stats
        return cls(
            run=RunRefView.of(snapshot.run),
            stream_length=stats.length,
            pending=stats.pending,
            lag=stats.lag,
            consumers=tuple(
                ConsumerView(
                    name=consumer.name,
                    pending=consumer.pending,
                    idle_ms=consumer.idle_ms,
                    active=consumer.active,
                )
                for consumer in stats.consumers
            ),
            rejected=stats.rejected,
            counted_sections=stats.counted,
            rate=round(snapshot.rate, RATE_DIGITS),
            peak_rate=round(snapshot.peak_rate, RATE_DIGITS),
            rates=tuple(round(rate, RATE_DIGITS) for rate in snapshot.rates),
        )


class BallotVoteView(View):
    number: int
    name: str
    votes: int


class BallotAuditView(View):
    section: str
    state: str
    issued_at: datetime
    received_at: datetime
    eligible_voters: int
    candidates: tuple[BallotVoteView, ...]
    blank: int
    null: int
    signature: str
    verified: bool | None

    @classmethod
    def of(cls, election: Election, audited: AuditedBallot) -> "BallotAuditView":
        ballot = audited.ballot
        names = {candidate.number: candidate.name for candidate in election.candidates}
        return cls(
            section=str(ballot.section),
            state=ballot.section.state.value,
            issued_at=ballot.issued_at,
            received_at=audited.received_at,
            eligible_voters=ballot.eligible_voters,
            candidates=tuple(
                BallotVoteView(number=number, name=names[number], votes=votes)
                for number, votes in sorted(
                    ballot.nominal_votes.items(), key=lambda item: -item[1]
                )
            ),
            blank=ballot.blank_votes,
            null=ballot.null_votes,
            signature=audited.signature,
            verified=audited.verified,
        )


class RejectionView(View):
    entry: str
    at: datetime
    reason: str
    section: str | None

    @classmethod
    def of(cls, rejection: Rejection) -> "RejectionView":
        return cls(
            entry=rejection.entry,
            at=rejection.at,
            reason=rejection.reason,
            section=rejection.section,
        )


class TamperView(View):
    section: str
    source: str
