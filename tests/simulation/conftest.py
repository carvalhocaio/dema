import pytest

from dema.sections.catalog import SectionCatalog
from dema.sections.synthetic import SyntheticSectionSource
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND


@pytest.fixture(scope="session")
def catalog() -> SectionCatalog:
    return SyntheticSectionSource(20_000).load()


@pytest.fixture(scope="session")
def ballots(catalog: SectionCatalog) -> SimulatedBallots:
    return BallotGenerator(DEMA_2026_FIRST_ROUND).generate(catalog)
