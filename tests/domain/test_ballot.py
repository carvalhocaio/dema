import pytest

from tests.factories import KEONS, NICO, make_ballot


def test_computes_turnout_and_abstentions() -> None:
    ballot = make_ballot()

    assert ballot.valid_votes == 270
    assert ballot.turnout == 285
    assert ballot.abstentions == 115


def test_rejects_turnout_above_electorate() -> None:
    with pytest.raises(ValueError, match="exceeds electorate"):
        make_ballot(eligible_voters=100)


def test_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="negative"):
        make_ballot(blank_votes=-1)


def test_nominal_votes_are_immutable() -> None:
    ballot = make_ballot()

    with pytest.raises(TypeError):
        ballot.nominal_votes[NICO.number] = 999  # type: ignore[index]


def test_ballot_is_decoupled_from_caller_dict() -> None:
    votes = {NICO.number: 10, KEONS.number: 5}
    ballot = make_ballot(nominal_votes=votes)

    votes[NICO.number] = 999

    assert ballot.nominal_votes[NICO.number] == 10
