from dataclasses import dataclass
from typing import Protocol

from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.runtime.active import ActiveRuns
from dema.storage.ballots import PostgresBallotRepository
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.tallying.store import AsyncTallyStore
from dema.workers.repository import BallotRepository


@dataclass(frozen=True, slots=True)
class Lane:
    run_id: int
    stream: BallotStream
    repository: BallotRepository
    store: AsyncTallyStore


class Lanes(Protocol):
    async def current(self) -> Lane: ...


class FixedLane:
    def __init__(self, lane: Lane) -> None:
        self._lane = lane

    async def current(self) -> Lane:
        return self._lane


class ActiveLanes:
    def __init__(
        self, active: ActiveRuns, redis: Redis, connection: AsyncConnection
    ) -> None:
        self._active = active
        self._redis = redis
        self._connection = connection
        self._lane: Lane | None = None

    async def current(self) -> Lane:
        record = await self._active.current()
        if self._lane is None or self._lane.run_id != record.run.id:
            election = record.election
            self._lane = Lane(
                run_id=record.run.id,
                stream=BallotStream(self._redis, record.keys, run_id=record.run.id),
                repository=PostgresBallotRepository(
                    self._connection, election, record.run.id
                ),
                store=RedisTallyStore(self._redis, record.keys, election),
            )
        return self._lane
