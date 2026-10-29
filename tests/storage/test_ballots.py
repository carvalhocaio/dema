import pytest
from psycopg import AsyncConnection

from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner, VerifiedBallot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from tests.helpers import SIGNING_KEY, expected_tally

pytestmark = pytest.mark.integration


def verify_all(ballots: list[Ballot]) -> list[VerifiedBallot]:
    signer = BallotSigner(SIGNING_KEY)
    return [signer.verify(signer.sign(ballot)) for ballot in ballots]


@pytest.fixture
def repository(async_connection: AsyncConnection) -> PostgresBallotRepository:
    return PostgresBallotRepository(async_connection, DEMA_2026_FIRST_ROUND.election)


async def test_saves_ballots_with_votes(
    repository: PostgresBallotRepository,
    async_connection: AsyncConnection,
    small_ballots: list[Ballot],
) -> None:
    assert await repository.save_many(verify_all(small_ballots[:10])) == 10

    cursor = await async_connection.execute("SELECT count(*) FROM ballot_votes")
    assert await cursor.fetchone() == (50,)


async def test_ignores_already_saved_ballots(
    repository: PostgresBallotRepository,
    async_connection: AsyncConnection,
    small_ballots: list[Ballot],
) -> None:
    await repository.save_many(verify_all(small_ballots[:10]))

    assert await repository.save_many(verify_all(small_ballots[5:15])) == 5
    cursor = await async_connection.execute("SELECT count(*) FROM ballot_votes")
    assert await cursor.fetchone() == (75,)


async def test_rebuilds_tally_from_saved_ballots(
    repository: PostgresBallotRepository,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    half = small_ballots[: len(small_ballots) // 2]
    await repository.save_many(verify_all(half))

    assert await repository.tally() == expected_tally(small_catalog, half)
    assert sorted(await repository.counted_sections()) == sorted(
        str(ballot.section) for ballot in half
    )


async def test_saving_nothing_is_a_no_op(repository: PostgresBallotRepository) -> None:
    assert await repository.save_many([]) == 0


async def test_deduplicates_ballots_within_a_batch(
    repository: PostgresBallotRepository,
    async_connection: AsyncConnection,
    small_ballots: list[Ballot],
) -> None:
    verified = verify_all(small_ballots[:3])

    assert await repository.save_many(verified + verified) == 3
    cursor = await async_connection.execute("SELECT count(*) FROM ballot_votes")
    assert await cursor.fetchone() == (15,)
