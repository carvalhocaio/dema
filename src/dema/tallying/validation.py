from dema.domain.ballot import Ballot
from dema.domain.election import Election


class UnknownCandidateError(ValueError):
    pass


def ensure_known_candidates(election: Election, ballot: Ballot) -> None:
    unknown = ballot.nominal_votes.keys() - election.candidate_numbers
    if unknown:
        raise UnknownCandidateError(f"unknown candidates: {sorted(unknown)}")
