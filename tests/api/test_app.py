import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from dema.api.app import create_app
from dema.config import Settings
from dema.domain.election import ElectionRound
from tests.api.fakes import (
    FIRST_RECORD,
    SECOND_RECORD,
    SECOND_ROUND,
    FakeArchive,
    FakePipeline,
    FakeSource,
    first_round_record,
    make_pipeline,
    make_tally,
)

SETTINGS = Settings(
    broadcast_interval=0.01,
    pipeline_interval=3_600,
    cors_origins=["http://localhost:3000"],
)
RUNS_SETTINGS = SETTINGS.model_copy(update={"allow_runs": True})


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
    archive = FakeArchive(
        (FIRST_RECORD, SECOND_RECORD), {ElectionRound.FIRST: first_round}
    )
    return TestClient(create_app(SETTINGS, archive, lambda _: source))


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
    assert body["margin"] == {
        "leader": 27,
        "remaining_electorate": 1_800,
        "leader_votes": 600,
        "votes_to_majority": (1_000 + 1_800) // 2 + 1 - 600,
        "runoff_gap": 400,
    }
    assert body["run"] == {"id": 1, "round": 1, "seed": 40}


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
    assert final["run"] == {"id": 1, "round": 1, "seed": 40}
    assert (final["verdict"], final["finalists"]) == ("elected", [27])
    assert final["progress"]["is_complete"] is True
    assert [c["number"] for c in live["candidates"]] == [27, 99]


def test_reports_unavailable_before_the_tally_is_ready() -> None:
    with TestClient(create_app(SETTINGS, FakeArchive(), lambda _: FakeSource())) as c:
        response = c.get("/rounds/1/results")

    assert response.status_code == 503
    assert response.json() == {"detail": "election is not set up yet"}


def test_lists_no_rounds_before_any_run() -> None:
    archive = FakeArchive(family=())
    with TestClient(create_app(SETTINGS, archive, lambda _: FakeSource())) as client:
        rounds = client.get("/rounds").json()
        results = client.get("/rounds/1/results")
        stream = client.get("/rounds/1/stream")

    assert rounds == []
    assert results.status_code == stream.status_code == 404


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
    assert body["lead_changes"] == [second["at"]]


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


def test_serves_the_tally_per_state(client: TestClient) -> None:
    body = client.get("/rounds/1/states").json()

    sp, zz = body["states"]
    assert (body["year"], body["round"]) == (2026, 1)
    assert (sp["state"], sp["region"]) == ("SP", "southeast")
    assert (sp["counted_sections"], sp["total_sections"]) == (4, 10)
    assert sp["progress"] == 0.4
    assert sp["leader"] == 27
    assert [c["number"] for c in sp["candidates"][:2]] == [27, 99]
    assert sp["candidates"][0]["share"] == pytest.approx(500 / 900)
    assert (zz["state"], zz["region"], zz["leader"]) == ("ZZ", "abroad", None)
    assert (zz["counted_sections"], zz["progress"]) == (0, 0.0)
    assert all(c["votes"] == 0 for c in zz["candidates"])


def test_states_of_a_missing_round_are_not_found(client: TestClient) -> None:
    assert client.get("/rounds/2/states").status_code == 404


def test_reports_the_current_run_and_whether_new_counts_are_allowed(
    client: TestClient,
) -> None:
    assert client.get("/runs/current").json() == {
        "run": {"id": 1, "round": 1, "seed": 40, "status": "counting"},
        "runs_enabled": False,
    }


def test_reports_no_current_run_before_setup() -> None:
    archive = FakeArchive(family=())
    with TestClient(create_app(SETTINGS, archive, lambda _: FakeSource())) as client:
        body = client.get("/runs/current").json()

    assert body == {"run": None, "runs_enabled": False}


def test_refuses_new_counts_unless_enabled(client: TestClient) -> None:
    response = client.post("/runs", json={"seed": 7})

    assert response.status_code == 403
    assert "DEMA_ALLOW_RUNS" in response.json()["detail"]


def runs_client(archive: FakeArchive) -> TestClient:
    return TestClient(create_app(RUNS_SETTINGS, archive, lambda _: FakeSource()))


def test_requests_a_new_count_with_the_chosen_seed_and_speed() -> None:
    archive = FakeArchive()
    with runs_client(archive) as client:
        response = client.post("/runs", json={"seed": 7, "speed": 600})

    assert response.status_code == 202
    assert response.json() == {"id": 99, "round": 1, "seed": 7, "status": "preparing"}
    assert archive.requests == [(7, 600.0)]


def test_draws_a_seed_when_none_is_given() -> None:
    archive = FakeArchive()
    with runs_client(archive) as client:
        response = client.post("/runs")

    [(seed, speed)] = archive.requests
    assert response.json()["seed"] == seed
    assert 0 <= seed < 1_000_000
    assert speed is None


def test_rejects_invalid_count_requests() -> None:
    with runs_client(FakeArchive()) as client:
        assert client.post("/runs", json={"seed": -1}).status_code == 422
        assert client.post("/runs", json={"speed": 0}).status_code == 422


def test_new_counts_need_a_prepared_election() -> None:
    with runs_client(FakeArchive(family=())) as client:
        response = client.post("/runs", json={"seed": 7})

    assert response.status_code == 503


def test_allows_posting_from_the_frontend_only_when_enabled() -> None:
    preflight = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    }
    with runs_client(FakeArchive()) as enabled:
        allowed = enabled.options("/runs", headers=preflight)
    with TestClient(create_app(SETTINGS, FakeArchive(), lambda _: FakeSource())) as c:
        refused = c.options("/runs", headers=preflight)

    assert "POST" in allowed.headers["access-control-allow-methods"]
    assert refused.status_code == 400


def test_stream_announces_a_new_run_and_follows_it() -> None:
    archive = FakeArchive()
    source = FakeSource(make_tally(counted_sections=4))
    app = create_app(SETTINGS, archive, lambda _: source)
    with (
        TestClient(app) as client,
        client.stream("GET", "/rounds/1/stream") as response,
    ):
        lines = response.iter_lines()
        [first] = read_events(lines, count=1)
        archive.records = (first_round_record(3, seed=7),)
        announced, followed = read_events(lines, count=2)

    assert first["data"]["run"]["id"] == 1
    assert (announced["event"], announced["data"]) == (
        "run",
        {"id": 3, "round": 1, "seed": 7},
    )
    assert (followed["event"], followed["data"]["run"]["id"]) == ("results", 3)


def test_stream_announces_the_runoff_and_closes() -> None:
    archive = FakeArchive()
    source = FakeSource(make_tally(counted_sections=4))
    app = create_app(SETTINGS, archive, lambda _: source)
    with (
        TestClient(app) as client,
        client.stream("GET", "/rounds/1/stream") as response,
    ):
        lines = response.iter_lines()
        read_events(lines, count=1)
        archive.records = (FIRST_RECORD, SECOND_RECORD)
        events = read_events(lines, count=5)

    assert [event["event"] for event in events] == ["run"]
    assert events[0]["data"] == {"id": 2, "round": 2, "seed": 40}


def pipeline_client(pipeline: FakePipeline, interval: float = 3_600) -> TestClient:
    settings = SETTINGS.model_copy(update={"pipeline_interval": interval})
    source = FakeSource(make_tally(counted_sections=4))
    return TestClient(create_app(settings, FakeArchive(), lambda _: source, pipeline))


def test_reports_the_pipeline_metrics() -> None:
    with pipeline_client(FakePipeline(make_pipeline())) as client:
        body = client.get("/pipeline").json()

    assert body == {
        "run": {"id": 1, "round": 1, "seed": 40},
        "stream_length": 12,
        "pending": 3,
        "lag": 5,
        "consumers": [
            {"name": "demo-0-0", "pending": 3, "idle_ms": 120, "active": True},
            {"name": "old", "pending": 0, "idle_ms": 9_000, "active": False},
        ],
        "rejected": 1,
        "counted_sections": 4,
        "rate": 12.3,
        "peak_rate": 40.0,
        "rates": [0.0, 12.3],
    }


def test_pipeline_is_unavailable_before_any_run() -> None:
    with pipeline_client(FakePipeline()) as client:
        response = client.get("/pipeline")

    assert response.status_code == 503


def test_streams_pipeline_metrics_alongside_the_results() -> None:
    pipeline = FakePipeline(make_pipeline())
    with (
        pipeline_client(pipeline, interval=0.01) as client,
        client.stream("GET", "/rounds/1/stream") as response,
    ):
        lines = response.iter_lines()
        events = read_events(lines, count=2)
        pipeline.snapshot = make_pipeline(counted=9)
        while (event := read_events(lines, count=1)[0])["event"] != "pipeline" or (
            event["data"]["counted_sections"] != 9
        ):
            continue

    assert {event["event"] for event in events} == {"results", "pipeline"}
