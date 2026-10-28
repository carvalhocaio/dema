from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from dema.domain.state import Region
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.simulation.scenario import RegionalProfile

BASE_PROFILE = RegionalProfile(
    preferences={KEONS.number: 0.5, NICO.number: 0.5},
    turnout=0.8,
    release_delay=timedelta(minutes=30),
)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"preferences": {KEONS.number: 0.0}}, "positive"),
        ({"turnout": 1.2}, "turnout"),
        ({"release_delay": timedelta(0)}, "delay"),
    ],
)
def test_profile_rejects_invalid_values(overrides: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(BASE_PROFILE, **overrides)


def test_scenario_requires_every_region() -> None:
    profiles = dict(DEMA_2026_FIRST_ROUND.profiles)
    del profiles[Region.ABROAD]

    with pytest.raises(ValueError, match="every region"):
        replace(DEMA_2026_FIRST_ROUND, profiles=profiles)


def test_scenario_requires_preferences_for_all_candidates() -> None:
    profiles = dict.fromkeys(Region, BASE_PROFILE)

    with pytest.raises(ValueError, match="exactly the election candidates"):
        replace(DEMA_2026_FIRST_ROUND, profiles=profiles)


def test_scenario_rejects_rates_without_valid_votes() -> None:
    with pytest.raises(ValueError, match="no room"):
        replace(DEMA_2026_FIRST_ROUND, blank_rate=0.5, null_rate=0.5)


def test_scenario_requires_aware_closing_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(DEMA_2026_FIRST_ROUND, polls_close=datetime(2026, 10, 4, 17))
