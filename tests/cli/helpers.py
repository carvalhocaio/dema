from dema.config import get_settings
from dema.runtime.active import ActiveRuns
from dema.storage.elections import ElectionRecord
from dema.wiring import open_database, open_redis


async def active_record() -> ElectionRecord:
    settings = get_settings()
    async with open_database(settings) as connection, open_redis(settings) as redis:
        return await ActiveRuns(redis, connection).current()
