import pytest

from dema.domain.state import Region
from dema.sections.catalog import SectionCatalog
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.simulation.sampler import MIN_TURNOUT, ScenarioSampler
from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.outcome import Outcome, Verdict, decide

REFERENCE = DEMA_2026_FIRST_ROUND
VARIETY_SEEDS = range(1, 41)


def outcome_for(seed: int, catalog: SectionCatalog) -> Outcome:
    scenario = ScenarioSampler(REFERENCE).sample(seed)
    store = InMemoryTallyStore(
        REFERENCE.election, len(catalog), catalog.total_electorate
    )
    for ballot in (
        BallotGenerator(scenario, seed=seed).generate(catalog).in_release_order()
    ):
        store.add(ballot)
    return decide(REFERENCE.election, store.snapshot())


def test_same_seed_draws_the_same_scenario() -> None:
    sampler = ScenarioSampler(REFERENCE)

    assert sampler.draw(7) == sampler.draw(7)
    assert sampler.sample(7) != sampler.sample(8)


def test_draw_keeps_the_election_and_covers_every_region() -> None:
    draw = ScenarioSampler(REFERENCE).draw(3)

    assert draw.scenario.election == REFERENCE.election
    assert draw.scenario.polls_close == REFERENCE.polls_close
    assert set(draw.scenario.profiles) == set(Region)
    assert sum(draw.national.values()) == pytest.approx(1)
    for profile in draw.scenario.profiles.values():
        assert sum(profile.preferences.values()) == pytest.approx(1)
        assert min(profile.preferences.values()) > 0


def test_regions_keep_the_reference_tilt() -> None:
    profiles = ScenarioSampler(REFERENCE).sample(1).profiles
    northeast = profiles[Region.NORTHEAST].preferences
    south = profiles[Region.SOUTH].preferences

    assert northeast[KEONS.number] / northeast[NICO.number] > (
        south[KEONS.number] / south[NICO.number]
    )


def test_turnout_moves_within_the_spread_and_stays_valid() -> None:
    sampler = ScenarioSampler(REFERENCE, turnout_spread=0.04)

    for seed in range(20):
        for region, profile in sampler.sample(seed).profiles.items():
            reference = REFERENCE.profiles[region].turnout
            assert abs(profile.turnout - reference) <= 0.04 + 1e-12
            assert MIN_TURNOUT <= profile.turnout <= 1


def test_turnout_is_clipped_to_a_valid_rate() -> None:
    sampler = ScenarioSampler(REFERENCE, turnout_spread=0.99)

    turnouts = [
        profile.turnout
        for seed in range(30)
        for profile in sampler.sample(seed).profiles.values()
    ]

    assert min(turnouts) == MIN_TURNOUT
    assert max(turnouts) == 1


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"national_concentration": 0}, "concentrations must be positive"),
        ({"regional_concentration": -1}, "concentrations must be positive"),
        ({"turnout_spread": -0.1}, "turnout spread"),
        ({"turnout_spread": 1}, "turnout spread"),
    ],
)
def test_rejects_invalid_parameters(overrides: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ScenarioSampler(REFERENCE, **overrides)


def test_seeds_produce_varied_but_plausible_elections(
    small_catalog: SectionCatalog,
) -> None:
    outcomes = [outcome_for(seed, small_catalog) for seed in VARIETY_SEEDS]
    usual_pair = {KEONS.number, NICO.number}

    assert any(o.verdict is Verdict.ELECTED for o in outcomes)
    assert any(
        o.verdict is Verdict.RUNOFF and {c.number for c in o.finalists} != usual_pair
        for o in outcomes
    )
    assert all(0.35 < o.leader.share < 0.75 for o in outcomes)
