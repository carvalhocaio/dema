from collections import Counter

from dema.domain.ballot import Ballot
from dema.domain.election import Election
from dema.domain.section import SectionKey
from dema.tallying.tally import Tally


class UnknownCandidateError(ValueError):
    pass


class InMemoryTallyStore:
    def __init__(
        self, election: Election, total_sections: int, total_electorate: int
    ) -> None:
        self._election = election
        self._total_sections = total_sections
        self._total_electorate = total_electorate
        self._counted: set[SectionKey] = set()
        self._votes: Counter[int] = Counter(
            dict.fromkeys(election.candidate_numbers, 0)
        )
        self._blank = 0
        self._null = 0
        self._electorate = 0

    def add(self, ballot: Ballot) -> bool:
        unknown = ballot.nominal_votes.keys() - self._election.candidate_numbers
        if unknown:
            raise UnknownCandidateError(f"unknown candidates: {sorted(unknown)}")
        if ballot.section in self._counted:
            return False
        self._counted.add(ballot.section)
        self._votes.update(ballot.nominal_votes)
        self._blank += ballot.blank_votes
        self._null += ballot.null_votes
        self._electorate += ballot.eligible_voters
        return True

    def snapshot(self) -> Tally:
        return Tally(
            nominal_votes=self._votes,
            blank_votes=self._blank,
            null_votes=self._null,
            counted_sections=len(self._counted),
            counted_electorate=self._electorate,
            total_sections=self._total_sections,
            total_electorate=self._total_electorate,
        )
