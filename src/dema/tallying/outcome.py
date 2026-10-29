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
class Outcome:
    verdict: Verdict
    ranking: tuple[CandidateResult, ...]
    finalists: tuple[Candidate, ...] = ()

    @property
    def leader(self) -> CandidateResult:
        return self.ranking[0]


def decide(election: Election, tally: Tally) -> Outcome:
    ranking = _rank(election, tally)
    if _has_secured_majority(ranking[0], tally):
        return Outcome(Verdict.ELECTED, ranking, (ranking[0].candidate,))
    if election.round is ElectionRound.SECOND:
        if tally.is_complete:
            return Outcome(Verdict.ELECTED, ranking, (ranking[0].candidate,))
        return Outcome(Verdict.UNDECIDED, ranking)
    if _has_secured_runoff(ranking, tally):
        finalists = (ranking[0].candidate, ranking[1].candidate)
        return Outcome(Verdict.RUNOFF, ranking, finalists)
    return Outcome(Verdict.UNDECIDED, ranking)


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


def _has_secured_majority(leader: CandidateResult, tally: Tally) -> bool:
    best_case_valid = tally.valid_votes + tally.remaining_electorate
    return leader.votes * 2 > best_case_valid


def _has_secured_runoff(ranking: tuple[CandidateResult, ...], tally: Tally) -> bool:
    remaining = tally.remaining_electorate
    _, runner_up, *chasers = ranking
    nobody_can_win = all(
        (result.votes + remaining) * 2 <= tally.valid_votes + remaining
        for result in ranking
    )
    if not nobody_can_win:
        return False
    if not chasers:
        return True
    return tally.is_complete or runner_up.votes - chasers[0].votes > remaining
