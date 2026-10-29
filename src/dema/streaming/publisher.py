import asyncio
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from datetime import datetime
from typing import Protocol

from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner, SignedBallot

MIN_SLEEP_SECONDS = 0.05

Clock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]


class BallotSink(Protocol):
    async def publish(self, ballots: Sequence[SignedBallot]) -> int: ...


class BallotPublisher:
    def __init__(
        self,
        sink: BallotSink,
        signer: BallotSigner,
        speed_factor: float,
        batch_size: int = 500,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if speed_factor <= 0:
            raise ValueError("speed factor must be positive")
        self._sink = sink
        self._signer = signer
        self._speed_factor = speed_factor
        self._batch_size = batch_size
        self._clock = clock
        self._sleep = sleep

    async def publish(self, ballots: Iterable[Ballot], polls_close: datetime) -> int:
        started = self._clock()
        pending: list[SignedBallot] = []
        published = 0
        for ballot in ballots:
            elapsed = self._clock() - started
            wait = self._release_offset(ballot, polls_close) - elapsed
            if wait >= MIN_SLEEP_SECONDS:
                published += await self._flush(pending)
                await self._sleep(wait)
            pending.append(self._signer.sign(ballot))
            if len(pending) >= self._batch_size:
                published += await self._flush(pending)
        return published + await self._flush(pending)

    def _release_offset(self, ballot: Ballot, polls_close: datetime) -> float:
        return (ballot.issued_at - polls_close).total_seconds() / self._speed_factor

    async def _flush(self, pending: list[SignedBallot]) -> int:
        published = await self._sink.publish(pending)
        pending.clear()
        return published
