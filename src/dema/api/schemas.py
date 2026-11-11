from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from dema.domain.election import Election
from dema.domain.state import Region
from dema.tallying.outcome import Outcome, Verdict, decide
from dema.tallying.states import StateTally
from dema.tallying.tally import Tally
from dema.tallying.timeline import Timeline


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


class ResultsView(View):
    year: int
    round: int
    progress: ProgressView
    votes: VotesView
    candidates: tuple[CandidateView, ...]
    verdict: Verdict
    finalists: tuple[int, ...]

    @classmethod
    def build(cls, election: Election, tally: Tally, outcome: Outcome) -> "ResultsView":
        return cls(
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
