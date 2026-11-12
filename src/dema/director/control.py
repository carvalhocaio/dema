from dataclasses import dataclass
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from dema.streaming.keys import CONTROL_STREAM, DIRECTOR_GROUP

Messages = list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]]


@dataclass(frozen=True, slots=True)
class CountRequest:
    run_id: int
    speed: float | None = None


class ControlStream:
    def __init__(self, redis: Redis, key: str = CONTROL_STREAM) -> None:
        self._redis = redis
        self._key = key

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._key, DIRECTOR_GROUP, id="$", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def request(self, request: CountRequest) -> None:
        speed = "" if request.speed is None else str(request.speed)
        await self._redis.xadd(self._key, {"run": request.run_id, "speed": speed})

    async def next(self, consumer: str, block_ms: int) -> CountRequest | None:
        response = await self._redis.xreadgroup(
            DIRECTOR_GROUP, consumer, {self._key: ">"}, 1, block_ms
        )
        entries = [
            entry
            for _, messages in cast(Messages, response or [])
            for entry in messages
        ]
        if not entries:
            return None
        entry_id, fields = entries[0]
        await self._redis.xack(self._key, DIRECTOR_GROUP, entry_id)
        speed = fields.get(b"speed", b"")
        return CountRequest(
            run_id=int(fields[b"run"]), speed=float(speed) if speed else None
        )
