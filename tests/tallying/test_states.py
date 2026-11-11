from dema.domain.state import State
from dema.tallying.states import StateCount, StateTotals, build_state_tallies
from tests.factories import KEONS, LISDEN, NICO, make_election

ELECTION = make_election()


def test_orders_states_and_fills_missing_ones_with_zeros() -> None:
    totals = [StateTotals(State.ZZ, 1, 50), StateTotals(State.AC, 3, 900)]
    counts = [StateCount(State.AC, 2, 600, 5, 5, {NICO.number: 100, KEONS.number: 250})]

    ac, zz = build_state_tallies(ELECTION, totals, counts)

    assert ac.state is State.AC
    assert ac.leader == KEONS.number
    assert ac.tally.nominal_votes == {
        NICO.number: 100,
        KEONS.number: 250,
        LISDEN.number: 0,
    }
    assert ac.tally.progress == 2 / 3
    assert zz.leader is None
    assert zz.tally.counted_sections == 0
    assert zz.tally.total_electorate == 50


def test_a_counted_state_without_valid_votes_has_no_leader() -> None:
    totals = [StateTotals(State.SP, 1, 10)]
    counts = [StateCount(State.SP, 1, 10, 3, 2, {})]

    [sp] = build_state_tallies(ELECTION, totals, counts)

    assert sp.leader is None
    assert sp.tally.blank_votes == 3
