from dema.domain.election import Election, ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.runoff import Runoff, RunoffGenerator
from dema.simulation.sampler import ScenarioDraw, ScenarioSampler
from dema.simulation.scenario import Scenario

REFERENCE_SCENARIO: Scenario = DEMA_2026_FIRST_ROUND


def draw_scenario(seed: int) -> ScenarioDraw:
    return ScenarioSampler(REFERENCE_SCENARIO).draw(seed)


def simulate(
    scenario: Scenario, catalog: SectionCatalog, seed: int
) -> SimulatedBallots:
    return BallotGenerator(scenario, seed=seed).generate(catalog)


def simulate_first_round(catalog: SectionCatalog, seed: int) -> SimulatedBallots:
    return simulate(draw_scenario(seed).scenario, catalog, seed)


def ballots_election(ballots: SimulatedBallots, round_: ElectionRound) -> Election:
    reference = REFERENCE_SCENARIO.election
    return Election(
        year=reference.year,
        round=round_,
        candidates=tuple(reference.candidate(n) for n in ballots.candidate_numbers),
    )


def derive_runoff(first_round: SimulatedBallots, seed: int) -> Runoff:
    election = ballots_election(first_round, ElectionRound.FIRST)
    return RunoffGenerator(REFERENCE_SCENARIO, seed=seed).generate(
        first_round, election
    )
