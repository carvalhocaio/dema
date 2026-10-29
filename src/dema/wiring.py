from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.config import Settings
from dema.integrity.signer import BallotSigner
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.scenario import Scenario
from dema.streaming.keys import ElectionKeys

ACTIVE_SCENARIO: Scenario = DEMA_2026_FIRST_ROUND
ACTIVE_KEYS = ElectionKeys.for_election(ACTIVE_SCENARIO.election)


class MissingSigningKeyError(RuntimeError):
    pass


def build_signer(settings: Settings) -> BallotSigner:
    if settings.signing_key is None:
        raise MissingSigningKeyError(
            "set DEMA_SIGNING_KEY, e.g. with: "
            "python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    return BallotSigner(settings.signing_key.get_secret_value().encode())


@asynccontextmanager
async def open_redis(settings: Settings) -> AsyncIterator[Redis]:
    client = Redis.from_url(str(settings.redis_url))
    try:
        yield client
    finally:
        await client.aclose()


@asynccontextmanager
async def open_database(settings: Settings) -> AsyncIterator[AsyncConnection]:
    connection = await AsyncConnection.connect(
        str(settings.database_url), autocommit=True
    )
    async with connection:
        yield connection
