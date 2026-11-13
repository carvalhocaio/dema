import argparse
import runpy
import signal
import socket
from collections.abc import Sequence
from typing import ClassVar

import pytest
from pydantic import SecretStr

from dema import cli
from dema.cli import demo, main, workers
from dema.config import Settings
from dema.demo.readiness import DemoError


class FakeSupervisor:
    instances: ClassVar[list["FakeSupervisor"]] = []

    def __init__(self, env: dict[str, str]) -> None:
        self.env = env
        self.started: list[tuple[str, list[str]]] = []
        self.stopped: bool | None = None
        FakeSupervisor.instances.append(self)

    def start(self, name: str, argv: Sequence[str]) -> None:
        self.started.append((name, list(argv)))

    def exited(self) -> str | None:
        return "api"

    def stop(self, signalled: bool = False) -> None:
        self.stopped = signalled


@pytest.fixture
def staged(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []
    FakeSupervisor.instances = []
    monkeypatch.setattr(demo, "Supervisor", FakeSupervisor)
    monkeypatch.setattr(
        demo,
        "prepare_database",
        lambda url, year, sections: calls.append(("prepare", year, sections)) or 5_000,
    )
    monkeypatch.setattr(
        demo.signal, "signal", lambda signum, handler: calls.append(("signal", signum))
    )
    monkeypatch.setattr(demo, "api_healthy", lambda url: True)
    monkeypatch.setattr(demo, "director_listening", lambda url: True)

    def count(url: str, seed: int | None, speed: float) -> dict:
        calls.append(("count", url, seed, speed))
        return {"id": 3, "seed": 40}

    monkeypatch.setattr(demo, "request_count", count)
    return calls


def test_runs_the_pipeline_and_one_count(
    staged: list[tuple],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(demo, "get_settings", lambda: Settings(signing_key=None))

    main(["demo", "--seed", "40", "--speed", "300", "--workers", "1", "--port", "8123"])

    [supervisor] = FakeSupervisor.instances
    assert [name for name, _ in supervisor.started] == ["director", "demo-0", "api"]
    assert supervisor.started[1][1][-4:] == ["workers", "run", "--name", "demo-0"]
    assert supervisor.env["DEMA_ALLOW_RUNS"] == "true"
    assert supervisor.stopped is False
    assert staged == [
        ("signal", signal.SIGTERM),
        ("prepare", 2026, 5_000),
        ("count", "http://127.0.0.1:8123", 40, 300.0),
        ("signal", signal.SIGINT),
    ]
    output = capsys.readouterr().out
    assert "warning: DEMA_SIGNING_KEY is not set" in output
    assert "counting run #3 (seed 40) at http://localhost:3000" in output
    assert "api stopped; shutting down" in output


def test_ctrl_c_stops_every_process(
    staged: list[tuple],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        demo, "get_settings", lambda: Settings(signing_key=SecretStr("x" * 64))
    )

    def interrupt(url: str, seed: int | None, speed: float) -> dict:
        raise KeyboardInterrupt

    monkeypatch.setattr(demo, "request_count", interrupt)

    demo._demo(argparse.Namespace(sections=10, speed=1.0, seed=None, workers=0, port=1))

    output = capsys.readouterr().out
    assert "warning" not in output
    assert output.endswith("stopping\n")
    assert FakeSupervisor.instances[0].stopped is True


def test_stops_the_children_when_the_demo_cannot_start(
    staged: list[tuple], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(demo, "get_settings", lambda: Settings(signing_key=None))

    def fail(url: str, seed: int | None, speed: float) -> dict:
        raise DemoError("api stopped before the demo was ready")

    monkeypatch.setattr(demo, "request_count", fail)

    with pytest.raises(SystemExit, match="api stopped"):
        main(["demo", "--workers", "0"])

    assert FakeSupervisor.instances[0].stopped is False


def test_sigterm_stops_like_ctrl_c() -> None:
    with pytest.raises(KeyboardInterrupt):
        demo.interrupt(signal.SIGTERM, None)


def test_watch_waits_for_the_first_child_to_stop() -> None:
    answers = iter([None, None, "worker"])
    naps: list[float] = []

    assert demo.watch(lambda: next(answers), naps.append) == "worker"
    assert naps == [0.5, 0.5]


def test_workers_take_a_consumer_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    consumers: list[str] = []
    monkeypatch.setattr(workers, "_work", consumers.append)

    main(["workers", "run", "--name", "demo-7"])
    main(["workers", "run"])

    assert consumers == ["demo-7-0", f"{socket.gethostname()}-0"]


def test_module_entry_point_runs_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli, "main", lambda: calls.append("main"))

    runpy.run_module("dema", run_name="__main__")

    assert calls == ["main"]
