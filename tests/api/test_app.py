import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from dema.api.app import create_app
from dema.config import Settings
from dema.domain.election import ElectionRound
from tests.api.fakes import SECOND_ROUND, FakeArchive, FakeSource, make_tally

SETTINGS = Settings(broadcast_interval=0.01, cors_origins=["http://localhost:3000"])
RUNOFF_SETTINGS = SETTINGS.model_copy(update={"round": ElectionRound.SECOND})
BOTH = (ElectionRound.FIRST, ElectionRound.SECOND)


@pytest.fixture
def source() -> FakeSource:
    return FakeSource(make_tally(counted_sections=4))


@pytest.fixture
def archive() -> FakeArchive:
    return FakeArchive()


@pytest.fixture
def client(source: FakeSource, archive: FakeArchive) -> Iterator[TestClient]:
    with TestClient(create_app(SETTINGS, archive, lambda _: source)) as client:
        yield client


def runoff_client(source: FakeSource) -> TestClient:
    first_round = make_tally(counted_sections=10, keons=480, nico=420)
    archive = FakeArchive(BOTH, {ElectionRound.FIRST: first_round})
    return TestClient(create_app(RUNOFF_SETTINGS, archive, lambda _: source))


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


def test_lists_rounds_with_the_active_one_live() -> None:
    source = FakeSource(make_tally(4, election=SECOND_ROUND))
    with runoff_client(source) as client:
        body = client.get("/rounds").json()

    assert body == [
        {"round": 1, "status": "final"},
        {"round": 2, "status": "live"},
    ]


def test_returns_live_results_for_the_active_round(
    client: TestClient, archive: FakeArchive
) -> None:
    body = client.get("/rounds/1/results").json()

    assert body["progress"]["counted_sections"] == 4
    assert body["candidates"][0]["name"] == "Keons"
    assert body["verdict"] == "undecided"
    assert archive.loads == [(2026, ElectionRound.FIRST)]


def test_returns_fresh_live_results_on_each_request(
    client: TestClient, source: FakeSource
) -> None:
    source.tally = make_tally(counted_sections=10)

    assert client.get("/rounds/1/results").json()["verdict"] == "elected"


def test_reads_finished_rounds_from_the_archive() -> None:
    source = FakeSource(make_tally(4, election=SECOND_ROUND))
    with runoff_client(source) as client:
        final = client.get("/rounds/1/results").json()
        live = client.get("/rounds/2/results").json()

    assert final["round"] == 1
    assert (final["verdict"], final["finalists"]) == ("elected", [27])
    assert final["progress"]["is_complete"] is True
    assert [c["number"] for c in live["candidates"]] == [27, 99]


@pytest.mark.parametrize(
    ("archive", "source"),
    [
        (FakeArchive(rounds=()), FakeSource(make_tally(4))),
        (FakeArchive(), FakeSource()),
    ],
    ids=["no election in the database", "no tally in redis"],
)
def test_reports_unavailable_before_setup(
    archive: FakeArchive, source: FakeSource
) -> None:
    with TestClient(create_app(SETTINGS, archive, lambda _: source)) as client:
        response = client.get("/rounds/1/results")

    assert response.status_code == 503
    assert response.json() == {"detail": "election is not set up yet"}


def test_reports_rounds_that_were_never_set_up(client: TestClient) -> None:
    for path in ("/rounds/2/results", "/rounds/2/timeline"):
        response = client.get(path)

        assert response.status_code == 404
        assert response.json() == {"detail": "round 2 is not set up"}


def test_rejects_unknown_rounds(client: TestClient) -> None:
    assert client.get("/rounds/3/results").status_code == 422


def test_allows_frontend_origin(client: TestClient) -> None:
    response = client.get("/rounds", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_streams_the_active_round_as_server_sent_events(
    client: TestClient, source: FakeSource
) -> None:
    with client.stream("GET", "/rounds/1/stream") as response:
        lines = response.iter_lines()
        [first] = read_events(lines, count=1)
        source.tally = make_tally(counted_sections=7)
        [second] = read_events(lines, count=1)

    assert response.headers["content-type"].startswith("text/event-stream")
    assert (first["event"], first["id"]) == ("results", "4")
    assert first["data"]["progress"]["counted_sections"] == 4
    assert second["id"] == "7"


def test_only_the_active_round_streams(client: TestClient) -> None:
    response = client.get("/rounds/2/stream")

    assert response.status_code == 404
    assert response.json() == {"detail": "round 2 is not being counted"}


def test_serves_the_minute_by_minute_timeline(client: TestClient) -> None:
    body = client.get("/rounds/1/timeline").json()

    first, second = body["points"]
    assert (body["year"], body["round"]) == (2026, 1)
    assert first["at"] == "2026-10-04T20:00:00Z"
    assert first["progress"] == 0.5
    assert first["shares"]["27"] == 0.4
    assert set(first["shares"]) == {"12", "27", "31", "44", "99"}
    assert first["verdict"] == "undecided"
    assert second["shares"]["27"] == 0.65
    assert body["decided_at"] == second["at"] == "2026-10-04T20:03:00Z"


def test_serves_a_full_results_view_per_replay_minute(client: TestClient) -> None:
    body = client.get("/rounds/1/replay").json()
    timeline = client.get("/rounds/1/timeline").json()

    first, second = body["points"]
    assert (body["year"], body["round"]) == (2026, 1)
    assert [p["at"] for p in body["points"]] == [p["at"] for p in timeline["points"]]
    assert first["results"]["progress"]["counted_sections"] == 5
    assert first["results"]["candidates"][0]["share"] == 0.6
    assert second["results"]["verdict"] == timeline["points"][1]["verdict"]
    assert second["results"]["votes"]["turnout"] == 2_050


def test_replay_of_a_missing_round_is_not_found(client: TestClient) -> None:
    response = client.get("/rounds/2/replay")

    assert response.status_code == 404


def test_compresses_large_responses(client: TestClient) -> None:
    response = client.get("/rounds/1/replay", headers={"Accept-Encoding": "gzip"})

    assert response.headers.get("content-encoding") == "gzip"
