import asyncio
import logging
from collections.abc import Sequence
from typing import Protocol

from dema.integrity.signer import BallotSigner, InvalidSignatureError, VerifiedBallot
from dema.streaming.stream import BallotStream, StreamEntry
from dema.tallying.store import AsyncTallyStore

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 1.0


class BallotRepository(Protocol):
    async def save_many(self, verified: Sequence[VerifiedBallot]) -> int: ...


class TallyWorker:
    def __init__(
        self,
        stream: BallotStream,
        signer: BallotSigner,
        repository: BallotRepository,
        store: AsyncTallyStore,
        consumer: str,
        batch_size: int = 500,
        block_ms: int = 1_000,
        stale_after_ms: int = 30_000,
    ) -> None:
        self._stream = stream
        self._signer = signer
        self._repository = repository
        self._store = store
        self._consumer = consumer
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._stale_after_ms = stale_after_ms

    async def run(self, stop: asyncio.Event) -> None:
        await self._stream.ensure_group()
        while not stop.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("batch failed, it will be claimed again")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    async def run_once(self) -> int:
        entries = await self._stream.claim_stale(
            self._consumer, self._stale_after_ms, self._batch_size
        ) or await self._stream.read(self._consumer, self._batch_size, self._block_ms)
        verified: list[VerifiedBallot] = []
        for entry in entries:
            result = self._verify(entry)
            if isinstance(result, str):
                logger.warning("rejected %s: %s", entry.id, result)
                await self._stream.reject(entry, result)
            else:
                verified.append(result)
        await self._repository.save_many(verified)
        await self._store.add_many([v.ballot for v in verified])
        await self._stream.acknowledge(entries)
        return len(entries)

    def _verify(self, entry: StreamEntry) -> VerifiedBallot | str:
        if entry.signed is None:
            return "malformed entry"
        try:
            return self._signer.verify(entry.signed)
        except InvalidSignatureError:
            return "invalid signature"
        except (ValueError, KeyError) as error:
            return f"invalid payload: {error!r}"
