import pytest

from dema.tallying.memory import InMemoryTallyStore, UnknownCandidateError
from tests.factories import KEONS, LISDEN, NICO, make_ballot, make_election


def make_store() -> InMemoryTallyStore:
    return InMemoryTallyStore(make_election(), total_sections=4, total_electorate=1_600)


def test_starts_empty_with_every_candidate() -> None:
    tally = make_store().snapshot()

    assert dict(tally.nominal_votes) == {
        NICO.number: 0,
        KEONS.number: 0,
        LISDEN.number: 0,
    }
    assert tally.counted_sections == 0


def test_accumulates_ballots() -> None:
    store = make_store()

    assert store.add(make_ballot(section_number=1))
    assert store.add(make_ballot(section_number=2))
    tally = store.snapshot()

    assert tally.nominal_votes[NICO.number] == 300
    assert tally.nominal_votes[KEONS.number] == 240
    assert (tally.blank_votes, tally.null_votes) == (10, 20)
    assert (tally.counted_sections, tally.counted_electorate) == (2, 800)


def test_ignores_duplicated_sections() -> None:
    store = make_store()
    store.add(make_ballot())

    assert not store.add(make_ballot())
    assert store.snapshot().nominal_votes[NICO.number] == 150


def test_rejects_unknown_candidates() -> None:
    with pytest.raises(UnknownCandidateError, match="13"):
        make_store().add(make_ballot(nominal_votes={13: 100}))


def test_snapshot_is_decoupled_from_store() -> None:
    store = make_store()
    snapshot = store.snapshot()

    store.add(make_ballot())

    assert snapshot.nominal_votes[NICO.number] == 0
