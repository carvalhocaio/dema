import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.director.control import CountRequest
from dema.domain.election import Election, ElectionRound
from dema.domain.run import Run, RunStatus
from dema.integrity.signer import BallotSigner
from dema.runtime.active import ActiveRuns
from dema.sections.catalog import SectionCatalog
from dema.services.counting import derive_runoff, simulate_first_round
from dema.services.runs import publish_ballots, start_run
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.seed import load_catalog
from dema.tallying.outcome import Verdict, decide
from dema.tallying.redis_store import RedisTallyStore
from dema.tallying.tally import Tally

SeedElection = Callable[[Election, datetime], Awaitable[None]]

POLL_SECONDS = 0.5


class RunCounter:
    def __init__(
        self,
        redis: Redis,
        connection: AsyncConnection,
        signer: BallotSigner,
        seed_election: SeedElection,
        speed_factor: float,
        batch_size: int,
        poll_seconds: float = POLL_SECONDS,
    ) -> None:
        self._redis = redis
        self._connection = connection
        self._active = ActiveRuns(redis, connection)
        self._signer = signer
        self._seed_election = seed_election
        self._speed_factor = speed_factor
        self._batch_size = batch_size
        self._poll_seconds = poll_seconds
        self._current: int | None = None

    async def count(self, request: CountRequest) -> None:
        run = await self._active.runs.get(request.run_id)
        self._current = run.id
        speed = request.speed or self._speed_factor
        catalog = await load_catalog(self._connection)
        ballots = simulate_first_round(catalog, run.seed)
        tally = await self._count_round(run, catalog, ballots, speed)
        record = await self._active.record(run.id)
        if decide(record.election, tally).verdict is not Verdict.RUNOFF:
            return
        runoff = derive_runoff(ballots, run.seed)
        await self._seed_election(runoff.election, SECOND_ROUND_POLLS_CLOSE)
        second = await self._active.runs.create(
            run.year,
            ElectionRound.SECOND,
            run.seed,
            [candidate.number for candidate in runoff.election.candidates],
            parent_id=run.id,
        )
        self._current = second.id
        await self._count_round(second, catalog, runoff.ballots, speed)

    async def abandon(self) -> None:
        if self._current is not None:
            await self._active.runs.finish(self._current, RunStatus.SUPERSEDED)
            self._current = None

    async def _count_round(
        self,
        run: Run,
        catalog: SectionCatalog,
        ballots: SimulatedBallots,
        speed: float,
    ) -> Tally:
        record = await start_run(
            self._active, self._redis, run, len(catalog), catalog.total_electorate
        )
        await publish_ballots(
            self._redis, record, self._signer, ballots, speed, self._batch_size
        )
        store = RedisTallyStore(self._redis, record.keys, record.election)
        tally = await store.snapshot()
        while not tally.is_complete:
            await asyncio.sleep(self._poll_seconds)
            tally = await store.snapshot()
        await self._active.runs.finish(run.id, RunStatus.COMPLETE)
        return tally
