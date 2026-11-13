from dataclasses import replace

import pytest
from redis.asyncio import Redis

from dema.integrity.signer import SignedBallot
from dema.monitoring.pipeline import (
    ConsumerState,
    PipelineCollector,
    read_stream_stats,
)
from dema.monitoring.rate import RateMeter
from dema.storage.elections import ElectionRecord
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from tests.api.fakes import FIRST_RECORD

pytestmark = pytest.mark.integration

KEYS = ElectionKeys.for_run(FIRST_RECORD.run)
SIGNED = SignedBallot(payload=b"{}", signature="00")


def test_a_consumer_is_active_while_it_keeps_polling() -> None:
    assert ConsumerState("demo-0-0", 0, idle_ms=1_000).active
    assert not ConsumerState("demo-0-0", 0, idle_ms=60_000).active


async def test_reads_an_empty_pipeline(redis_client: Redis) -> None:
    stats = await read_stream_stats(redis_client, KEYS)

    assert stats.length == stats.pending == stats.rejected == stats.counted == 0
    assert stats.lag == 0
    assert stats.consumers == ()


async def test_reports_backlog_before_any_worker_joins(redis_client: Redis) -> None:
    await BallotStream(redis_client, KEYS).publish([SIGNED] * 3)

    stats = await read_stream_stats(redis_client, KEYS)

    assert (stats.length, stats.pending, stats.lag) == (3, 0, 3)


async def test_reads_the_group_its_consumers_rejections_and_tally(
    redis_client: Redis,
) -> None:
    stream = BallotStream(redis_client, KEYS)
    await stream.ensure_group()
    await stream.publish([SIGNED] * 5)
    [first, *_] = await stream.read("worker-b", 2, 10)
    await stream.read("worker-a", 1, 10)
    await stream.acknowledge([first])
    await stream.reject(first, "invalid signature")
    await redis_client.sadd(KEYS.counted, "MT-1-1-1", "MT-1-1-2")

    stats = await read_stream_stats(redis_client, KEYS)

    assert (stats.length, stats.pending, stats.lag) == (5, 2, 2)
    assert (stats.rejected, stats.counted) == (1, 2)
    assert [(c.name, c.pending) for c in stats.consumers] == [
        ("worker-a", 1),
        ("worker-b", 1),
    ]
    assert all(consumer.active for consumer in stats.consumers)


async def test_collector_measures_the_active_run_and_restarts_on_a_new_one(
    redis_client: Redis,
) -> None:
    records = [FIRST_RECORD]
    ticks = iter([0.0, 1.0, 2.0])

    async def current() -> ElectionRecord:
        return records[-1]

    collector = PipelineCollector(
        redis_client,
        current,
        clock=lambda: next(ticks),
        meter=lambda: RateMeter(sample_seconds=1.0),
    )
    await collector.collect()
    await redis_client.sadd(KEYS.counted, *(f"MT-1-1-{n}" for n in range(40)))
    second = await collector.collect()
    records.append(replace(FIRST_RECORD, run=replace(FIRST_RECORD.run, id=2)))
    third = await collector.collect()

    assert (second.run.id, second.rate, second.rates) == (1, 40.0, (0.0, 40.0))
    assert second.stats.counted == 40
    assert (third.run.id, third.rates, third.peak_rate) == (2, (0.0,), 0.0)
