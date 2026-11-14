import asyncio
import logging

from dema.domain.election import ElectionNotSetUpError
from dema.integrity.signer import BallotSigner, InvalidSignatureError, VerifiedBallot
from dema.streaming.stream import StreamEntry
from dema.workers.lanes import Lane, Lanes

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 1.0
WAIT_FOR_RUN_SECONDS = 1.0


class TallyWorker:
    def __init__(
        self,
        lanes: Lanes,
        signer: BallotSigner,
        consumer: str,
        batch_size: int = 500,
        block_ms: int = 1_000,
        stale_after_ms: int = 30_000,
    ) -> None:
        self._lanes = lanes
        self._signer = signer
        self._consumer = consumer
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._stale_after_ms = stale_after_ms
        self._run_id: int | None = None

    async def run(self, stop: asyncio.Event) -> None:
        waiting = False
        while not stop.is_set():
            try:
                await self.run_once()
                waiting = False
            except ElectionNotSetUpError:
                if not waiting:
                    logger.info("waiting for a run to count")
                    waiting = True
                await asyncio.sleep(WAIT_FOR_RUN_SECONDS)
            except Exception:
                logger.exception("batch failed, it will be claimed again")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    async def run_once(self) -> int:
        lane = await self._switch()
        stream = lane.stream
        entries = await stream.claim_stale(
            self._consumer, self._stale_after_ms, self._batch_size
        ) or await stream.read(self._consumer, self._batch_size, self._block_ms)
        verified: list[VerifiedBallot] = []
        for entry in entries:
            if entry.run_id is not None and entry.run_id != lane.run_id:
                logger.info("skipped %s from run %s", entry.id, entry.run_id)
                continue
            result = self._verify(entry)
            if isinstance(result, str):
                logger.warning("rejected %s: %s", entry.id, result)
                await stream.reject(entry, result)
            else:
                verified.append(result)
        await lane.repository.save_many(verified)
        await lane.store.add_many([v.ballot for v in verified])
        await stream.acknowledge(entries)
        return len(entries)

    async def _switch(self) -> Lane:
        lane = await self._lanes.current()
        if lane.run_id != self._run_id:
            await lane.stream.ensure_group()
            self._run_id = lane.run_id
            logger.info("consuming run %s", lane.run_id)
        return lane

    def _verify(self, entry: StreamEntry) -> VerifiedBallot | str:
        if entry.signed is None:
            return "malformed entry"
        try:
            return self._signer.verify(entry.signed)
        except InvalidSignatureError:
            return "invalid signature"
        except (ValueError, KeyError) as error:
            return f"invalid payload: {error!r}"
