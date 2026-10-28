import pytest

from dema.domain.state import State
from dema.sections.synthetic import (
    MAX_VOTERS_PER_SECTION,
    MIN_VOTERS_PER_SECTION,
    SyntheticSectionSource,
)


def test_generates_requested_sections() -> None:
    assert len(SyntheticSectionSource(5_000).load()) == 5_000


def test_is_deterministic_per_seed() -> None:
    first = SyntheticSectionSource(1_000, seed=21).load()
    second = SyntheticSectionSource(1_000, seed=21).load()
    other = SyntheticSectionSource(1_000, seed=42).load()

    assert first.frame.equals(second.frame)
    assert not first.frame.equals(other.frame)


def test_keeps_voters_within_bounds() -> None:
    voters = SyntheticSectionSource(20_000).load().frame["eligible_voters"]

    assert voters.is_between(MIN_VOTERS_PER_SECTION, MAX_VOTERS_PER_SECTION).all()


def test_follows_electorate_weights() -> None:
    by_state = SyntheticSectionSource(50_000).load().electorate_by_state()

    assert set(by_state) == set(State)
    assert max(by_state, key=by_state.__getitem__) is State.SP
    assert by_state[State.MT] > by_state[State.RR]


def test_rejects_non_positive_count() -> None:
    with pytest.raises(ValueError, match="positive"):
        SyntheticSectionSource(0).load()
