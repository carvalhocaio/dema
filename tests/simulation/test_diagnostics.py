import pytest

from dema.simulation.ballots import SimulatedBallots
from dema.simulation.diagnostics import counting_timeline
from dema.simulation.presets import KEONS, NICO


def test_timeline_reaches_full_count(ballots: SimulatedBallots) -> None:
    timeline = counting_timeline(ballots, steps=4)

    assert [checkpoint.progress for checkpoint in timeline] == [0.25, 0.5, 0.75, 1.0]
    assert sum(timeline[-1].shares.values()) == pytest.approx(1)


def test_counting_turns_around(ballots: SimulatedBallots) -> None:
    timeline = counting_timeline(ballots, steps=20)

    assert timeline[0].leader == NICO.number
    assert timeline[-1].leader == KEONS.number


def test_rejects_non_positive_steps(ballots: SimulatedBallots) -> None:
    with pytest.raises(ValueError, match="positive"):
        counting_timeline(ballots, steps=0)
