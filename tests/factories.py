from datetime import UTC, datetime

from dema.domain.ballot import Ballot
from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionRound
from dema.domain.section import SectionKey
from dema.domain.state import State

NICO = Candidate(number=99, name="Nico", party="Dema Order")
KEONS = Candidate(number=27, name="Keons", party="Torchbearers")
LISDEN = Candidate(number=31, name="Lisden", party="Paladin Union")


def make_election(
    round_: ElectionRound = ElectionRound.FIRST,
    candidates: tuple[Candidate, ...] = (NICO, KEONS, LISDEN),
) -> Election:
    return Election(year=2026, round=round_, candidates=candidates)


def make_section_key(state: State = State.MT, number: int = 1) -> SectionKey:
    return SectionKey(state=state, municipality_code=90670, zone=1, number=number)


def make_ballot(
    nominal_votes: dict[int, int] | None = None,
    blank_votes: int = 5,
    null_votes: int = 10,
    eligible_voters: int = 400,
) -> Ballot:
    return Ballot(
        section=make_section_key(),
        eligible_voters=eligible_voters,
        nominal_votes=nominal_votes or {NICO.number: 150, KEONS.number: 120},
        blank_votes=blank_votes,
        null_votes=null_votes,
        issued_at=datetime(2026, 10, 4, 17, 0, tzinfo=UTC),
    )
