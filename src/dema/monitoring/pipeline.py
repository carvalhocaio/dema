import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from dema.domain.run import Run
from dema.monitoring.rate import RateMeter
from dema.storage.elections import ElectionRecord
from dema.streaming.keys import CONSUMER_GROUP, ElectionKeys

ACTIVE_WITHIN_MS = 5_000


@dataclass(frozen=True, slots=True)
class ConsumerState:
    name: str
    pending: int
    idle_ms: int

    @property
    def active(self) -> bool:
        return self.idle_ms < ACTIVE_WITHIN_MS


@dataclass(frozen=True, slots=True)
class StreamStats:
    length: int
    pending: int
    lag: int | None
    consumers: tuple[ConsumerState, ...]
    rejected: int
    counted: int


@dataclass(frozen=True, slots=True)
class PipelineSnapshot:
    run: Run
    stats: StreamStats
    rate: float
    peak_rate: float
    rates: tuple[float, ...]


async def read_stream_stats(
    redis: Redis, keys: ElectionKeys, group: str = CONSUMER_GROUP
) -> StreamStats:
    async with redis.pipeline(transaction=False) as pipe:
        pipe.xlen(keys.ballots)
        pipe.xlen(keys.rejected)
        pipe.scard(keys.counted)
        length, rejected, counted = await pipe.execute()
    info = await _group_info(redis, keys, group)
    if info is None:
        return StreamStats(length, 0, length, (), rejected, counted)
    return StreamStats(
        length=length,
        pending=info["pending"],
        lag=info["lag"],
        consumers=await _consumers(redis, keys, group),
        rejected=rejected,
        counted=counted,
    )


async def _group_info(
    redis: Redis, keys: ElectionKeys, group: str
) -> dict[str, Any] | None:
    try:
        groups = await redis.xinfo_groups(keys.ballots)
    except ResponseError:
        return None
    return next((info for info in groups if info["name"] == group.encode()), None)


async def _consumers(
    redis: Redis, keys: ElectionKeys, group: str
) -> tuple[ConsumerState, ...]:
    consumers = await redis.xinfo_consumers(keys.ballots, group)
    return tuple(
        sorted(
            (
                ConsumerState(
                    name=consumer["name"].decode(),
                    pending=consumer["pending"],
                    idle_ms=consumer["idle"],
                )
                for consumer in consumers
            ),
            key=lambda consumer: consumer.name,
        )
    )


class PipelineCollector:
    """Samples the active run's stream, consumer group and tally."""

    def __init__(
        self,
        redis: Redis,
        current: Callable[[], Awaitable[ElectionRecord]],
        clock: Callable[[], float] = time.monotonic,
        meter: Callable[[], RateMeter] = RateMeter,
    ) -> None:
        self._redis = redis
        self._current = current
        self._clock = clock
        self._new_meter = meter
        self._meter = meter()
        self._run_id: int | None = None

    async def collect(self) -> PipelineSnapshot:
        record = await self._current()
        if record.run.id != self._run_id:
            self._run_id = record.run.id
            self._meter = self._new_meter()
        stats = await read_stream_stats(self._redis, record.keys)
        self._meter.observe(self._clock(), stats.counted)
        return PipelineSnapshot(
            run=record.run,
            stats=stats,
            rate=self._meter.rate,
            peak_rate=self._meter.peak,
            rates=self._meter.history,
        )
