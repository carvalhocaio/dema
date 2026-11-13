import json
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

import pytest
from redis.asyncio import Redis

from dema.demo.readiness import (
    DemoError,
    api_healthy,
    director_listening,
    request_count,
    wait_until_ready,
)
from dema.streaming.keys import CONTROL_STREAM


class Handler(BaseHTTPRequestHandler):
    posted: ClassVar[list[dict]] = []

    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.posted.append(body)
        payload = json.dumps({"id": 3, "seed": body.get("seed", 9)}).encode()
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        return None


@pytest.fixture
def base_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    Handler.posted = []
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_reports_a_healthy_api(base_url: str) -> None:
    assert api_healthy(base_url) is True


def test_reports_an_unreachable_api() -> None:
    assert api_healthy(f"http://127.0.0.1:{free_port()}") is False


def test_requests_a_count_with_and_without_a_seed(base_url: str) -> None:
    assert request_count(base_url, 40, 600.0) == {"id": 3, "seed": 40}
    assert request_count(base_url, None, 120.0) == {"id": 3, "seed": 9}

    assert Handler.posted == [{"speed": 600.0, "seed": 40}, {"speed": 120.0}]


@pytest.mark.integration
async def test_knows_when_the_director_listens(
    redis_client: Redis, redis_url: str
) -> None:
    assert director_listening(redis_url) is False
    await redis_client.xgroup_create(CONTROL_STREAM, "other", id="$", mkstream=True)
    assert director_listening(redis_url) is False

    await redis_client.xgroup_create(CONTROL_STREAM, "director", id="$")

    assert director_listening(redis_url) is True


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.naps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.naps.append(seconds)
        self.now += seconds


def test_waits_until_every_check_passes() -> None:
    clock = Clock()
    answers = iter([False, False, True])

    wait_until_ready(
        [lambda: True, lambda: next(answers)],
        lambda: None,
        timeout=5,
        sleep=clock.sleep,
        clock=clock,
    )

    assert clock.naps == [0.2, 0.2]


def test_gives_up_when_a_child_stops() -> None:
    with pytest.raises(DemoError, match="api stopped before the demo was ready"):
        wait_until_ready([lambda: False], lambda: "api", timeout=5)


def test_gives_up_after_the_timeout() -> None:
    clock = Clock()

    with pytest.raises(DemoError, match="timed out"):
        wait_until_ready(
            [lambda: False], lambda: None, timeout=1, sleep=clock.sleep, clock=clock
        )
