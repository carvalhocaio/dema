from redis.asyncio import Redis

from dema.domain.run import Run
from dema.integrity.signer import BallotSigner
from dema.runtime.active import ActiveRuns
from dema.simulation.ballots import SimulatedBallots
from dema.storage.elections import ElectionRecord
from dema.streaming.publisher import BallotPublisher
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore


async def start_run(
    active: ActiveRuns,
    redis: Redis,
    run: Run,
    total_sections: int,
    total_electorate: int,
) -> ElectionRecord:
    record = await active.record(run.id)
    stream = BallotStream(redis, record.keys, run_id=run.id)
    await stream.clear()
    await stream.ensure_group()
    store = RedisTallyStore(redis, record.keys, record.election)
    await store.reset(total_sections, total_electorate)
    await active.activate(run.id)
    return await active.record(run.id)


async def publish_ballots(
    redis: Redis,
    record: ElectionRecord,
    signer: BallotSigner,
    ballots: SimulatedBallots,
    speed_factor: float,
    batch_size: int,
) -> int:
    stream = BallotStream(redis, record.keys, run_id=record.run.id)
    publisher = BallotPublisher(
        stream, signer, speed_factor=speed_factor, batch_size=batch_size
    )
    return await publisher.publish(ballots.in_release_order(), record.polls_close)
