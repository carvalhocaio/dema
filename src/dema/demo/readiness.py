import json
import time
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

import redis
from redis.exceptions import ResponseError

from dema.streaming.keys import CONTROL_STREAM, DIRECTOR_GROUP

POLL_SECONDS = 0.2


class DemoError(RuntimeError):
    pass


def api_healthy(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


def director_listening(redis_url: str) -> bool:
    client = redis.Redis.from_url(redis_url)
    try:
        groups = client.xinfo_groups(CONTROL_STREAM)
    except ResponseError:
        return False
    finally:
        client.close()
    return any(group["name"] == DIRECTOR_GROUP.encode() for group in groups)


def wait_until_ready(
    checks: Sequence[Callable[[], bool]],
    exited: Callable[[], str | None],
    timeout: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    deadline = clock() + timeout
    while not all(check() for check in checks):
        name = exited()
        if name is not None:
            raise DemoError(f"{name} stopped before the demo was ready")
        if clock() > deadline:
            raise DemoError("timed out waiting for the API and the director")
        sleep(POLL_SECONDS)


def request_count(base_url: str, seed: int | None, speed: float) -> dict[str, Any]:
    body: dict[str, Any] = {"speed": speed}
    if seed is not None:
        body["seed"] = seed
    request = urllib.request.Request(
        f"{base_url}/runs",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())
