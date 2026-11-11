from dataclasses import dataclass
from enum import StrEnum

from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionRound
from dema.tallying.tally import Tally


class Verdict(StrEnum):
    UNDECIDED = "undecided"
    ELECTED = "elected"
    RUNOFF = "runoff"


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate: Candidate
    votes: int
    share: float


@dataclass(frozen=True, slots=True)
class Margin:
    remaining_electorate: int
    leader_votes: int
    votes_to_majority: int
    runoff_gap: int | None

    @property
    def majority_secured(self) -> bool:
        return self.votes_to_majority == 0

    @property
    def runoff_secured(self) -> bool:
        return (
            self.runoff_gap is not None and self.runoff_gap > self.remaining_electorate
        )


@dataclass(frozen=True, slots=True)
class Outcome:
    verdict: Verdict
    ranking: tuple[CandidateResult, ...]
    margin: Margin
    finalists: tuple[Candidate, ...] = ()

    @property
    def leader(self) -> CandidateResult:
        return self.ranking[0]


def decide(election: Election, tally: Tally) -> Outcome:
    ranking = _rank(election, tally)
    margin = measure(ranking, tally)
    if margin.majority_secured:
        return Outcome(Verdict.ELECTED, ranking, margin, (ranking[0].candidate,))
    if election.round is ElectionRound.SECOND:
        if tally.is_complete:
            return Outcome(Verdict.ELECTED, ranking, margin, (ranking[0].candidate,))
        return Outcome(Verdict.UNDECIDED, ranking, margin)
    if _has_secured_runoff(ranking, margin, tally):
        finalists = (ranking[0].candidate, ranking[1].candidate)
        return Outcome(Verdict.RUNOFF, ranking, margin, finalists)
    return Outcome(Verdict.UNDECIDED, ranking, margin)


def measure(ranking: tuple[CandidateResult, ...], tally: Tally) -> Margin:
    leader = ranking[0]
    best_case_valid = tally.valid_votes + tally.remaining_electorate
    needed = best_case_valid // 2 + 1
    _, runner_up, *chasers = ranking
    return Margin(
        remaining_electorate=tally.remaining_electorate,
        leader_votes=leader.votes,
        votes_to_majority=max(0, needed - leader.votes),
        runoff_gap=runner_up.votes - chasers[0].votes if chasers else None,
    )


def _rank(election: Election, tally: Tally) -> tuple[CandidateResult, ...]:
    results = (
        CandidateResult(
            candidate=candidate,
            votes=tally.nominal_votes[candidate.number],
            share=tally.share(candidate.number),
        )
        for candidate in election.candidates
    )
    return tuple(
        sorted(results, key=lambda result: (-result.votes, result.candidate.birth_date))
    )


def _has_secured_runoff(
    ranking: tuple[CandidateResult, ...], margin: Margin, tally: Tally
) -> bool:
    remaining = margin.remaining_electorate
    nobody_can_win = all(
        (result.votes + remaining) * 2 <= tally.valid_votes + remaining
        for result in ranking
    )
    if not nobody_can_win:
        return False
    if margin.runoff_gap is None:
        return True
    return tally.is_complete or margin.runoff_secured
