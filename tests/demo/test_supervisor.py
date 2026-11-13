import signal
import subprocess
import sys
from collections.abc import Mapping, Sequence

from dema.demo.supervisor import Supervisor, spawn


class FakeProcess:
    def __init__(self, signals_to_stop: int | None) -> None:
        self.signals_to_stop = signals_to_stop
        self.received: list[int] = []
        self.killed = False
        self.code: int | None = None

    def poll(self) -> int | None:
        return self.code

    def send_signal(self, sig: int) -> None:
        self.received.append(sig)
        if self.signals_to_stop is not None and len(self.received) >= (
            self.signals_to_stop
        ):
            self.code = 0

    def wait(self, timeout: float | None = None) -> int:
        if self.code is None and timeout is not None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return 0

    def kill(self) -> None:
        self.killed = True
        self.code = -9


def supervised(*processes: FakeProcess) -> Supervisor:
    queue = list(processes)

    def start(argv: Sequence[str], env: Mapping[str, str]) -> FakeProcess:
        return queue.pop(0)

    supervisor = Supervisor({"A": "1"}, start=start, grace_seconds=0)
    for index, _ in enumerate(processes):
        supervisor.start(f"child-{index}", ["true"])
    return supervisor


def test_names_the_first_child_that_exited() -> None:
    running, stopped = FakeProcess(1), FakeProcess(1)
    supervisor = supervised(running, stopped)
    assert supervisor.exited() is None

    stopped.code = 1

    assert supervisor.exited() == "child-1"


def test_interrupts_twice_before_killing() -> None:
    polite, stubborn, deaf = FakeProcess(1), FakeProcess(2), FakeProcess(None)
    supervisor = supervised(polite, stubborn, deaf)

    supervisor.stop()

    assert polite.received == [signal.SIGINT]
    assert stubborn.received == [signal.SIGINT, signal.SIGINT]
    assert (polite.killed, stubborn.killed) == (False, False)
    assert deaf.killed is True


def test_spawns_real_processes_with_the_given_environment() -> None:
    process = spawn(
        [sys.executable, "-c", "import os, sys; sys.exit(int(os.environ['CODE']))"],
        {"CODE": "3"},
    )

    assert process.wait(timeout=10) == 3


def test_gives_interrupted_children_time_before_insisting() -> None:
    already_stopping, stubborn = FakeProcess(0), FakeProcess(1)
    already_stopping.code = 0
    supervisor = supervised(already_stopping, stubborn)

    supervisor.stop(signalled=True)

    assert already_stopping.received == []
    assert stubborn.received == [signal.SIGINT]
    assert stubborn.killed is False
