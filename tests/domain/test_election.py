import pytest

from dema.domain.election import ElectionRound
from tests.factories import KEONS, LISDEN, NICO, make_candidate, make_election


def test_rejects_duplicated_numbers() -> None:
    impostor = make_candidate(number=NICO.number, name="Vetomo")
    with pytest.raises(ValueError, match="unique"):
        make_election(candidates=(NICO, impostor))


def test_second_round_requires_two_candidates() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        make_election(round_=ElectionRound.SECOND, candidates=(NICO, KEONS, LISDEN))


def test_requires_at_least_two_candidates() -> None:
    with pytest.raises(ValueError, match="at least two"):
        make_election(candidates=(NICO,))


def test_finds_candidate_by_number() -> None:
    election = make_election()

    assert election.candidate(KEONS.number) is KEONS
    assert election.candidate_numbers == {NICO.number, KEONS.number, LISDEN.number}


def test_unknown_candidate_raises_key_error() -> None:
    with pytest.raises(KeyError):
        make_election().candidate(13)
