import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from dema.api.app import create_app
from dema.config import Settings
from tests.api.fakes import FakeSource, make_tally

SETTINGS = Settings(broadcast_interval=0.01, cors_origins=["http://localhost:3000"])


@pytest.fixture
def source() -> FakeSource:
    return FakeSource(make_tally(counted_sections=4))


@pytest.fixture
def client(source: FakeSource) -> Iterator[TestClient]:
    with TestClient(create_app(source, SETTINGS)) as client:
        yield client


def read_events(lines: Iterator[str], count: int) -> list[dict]:
    events: list[dict] = []
    event: dict = {}
    for line in lines:
        if not line:
            if "data" in event:
                events.append(event)
            event = {}
            if len(events) == count:
                return events
            continue
        field, _, value = line.partition(": ")
        event[field] = json.loads(value) if field == "data" else value
    return events


def test_reports_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_returns_current_results(client: TestClient) -> None:
    body = client.get("/results").json()

    assert body["progress"]["counted_sections"] == 4
    assert body["candidates"][0]["name"] == "Keons"
    assert body["verdict"] == "undecided"


def test_returns_fresh_results_on_each_request(
    client: TestClient, source: FakeSource
) -> None:
    source.tally = make_tally(counted_sections=10)

    assert client.get("/results").json()["verdict"] == "elected"


def test_reports_unavailable_before_setup() -> None:
    with TestClient(create_app(FakeSource(), SETTINGS)) as client:
        response = client.get("/results")

    assert response.status_code == 503
    assert response.json() == {"detail": "election is not set up yet"}


def test_allows_frontend_origin(client: TestClient) -> None:
    response = client.get("/results", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_streams_results_as_server_sent_events(
    client: TestClient, source: FakeSource
) -> None:
    with client.stream("GET", "/results/stream") as response:
        lines = response.iter_lines()
        [first] = read_events(lines, count=1)
        source.tally = make_tally(counted_sections=7)
        [second] = read_events(lines, count=1)

    assert response.headers["content-type"].startswith("text/event-stream")
    assert (first["event"], first["id"]) == ("results", "4")
    assert first["data"]["progress"]["counted_sections"] == 4
    assert second["id"] == "7"
