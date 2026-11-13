import signal
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class Process(Protocol):
    def poll(self) -> int | None: ...

    def send_signal(self, sig: int) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


Spawn = Callable[[Sequence[str], Mapping[str, str]], Process]


def spawn(argv: Sequence[str], env: Mapping[str, str]) -> Process:
    return subprocess.Popen(list(argv), env=dict(env))


@dataclass(frozen=True, slots=True)
class Child:
    name: str
    process: Process


class Supervisor:
    def __init__(
        self,
        env: Mapping[str, str],
        start: Spawn = spawn,
        grace_seconds: float = 10.0,
    ) -> None:
        self._env = env
        self._start = start
        self._grace = grace_seconds
        self._children: list[Child] = []

    def start(self, name: str, argv: Sequence[str]) -> None:
        self._children.append(Child(name, self._start(argv, self._env)))

    def exited(self) -> str | None:
        return next(
            (
                child.name
                for child in self._children
                if child.process.poll() is not None
            ),
            None,
        )

    def stop(self, signalled: bool = False) -> None:
        if signalled:
            self._wait()
        for attempt in (signal.SIGINT,) if signalled else (signal.SIGINT,) * 2:
            for child in self._running():
                child.process.send_signal(attempt)
            self._wait()
        for child in self._running():
            child.process.kill()
            child.process.wait()

    def _wait(self) -> None:
        for child in self._running():
            try:
                child.process.wait(timeout=self._grace)
            except subprocess.TimeoutExpired:
                continue

    def _running(self) -> list[Child]:
        return [child for child in self._children if child.process.poll() is None]
