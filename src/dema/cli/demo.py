import argparse
import os
import signal
import sys
import time
from collections.abc import Callable
from types import FrameType

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.demo.readiness import (
    api_healthy,
    director_listening,
    request_count,
    wait_until_ready,
)
from dema.demo.setup import demo_environment, prepare_database
from dema.demo.supervisor import Supervisor

READY_TIMEOUT_SECONDS = 60.0
WATCH_SECONDS = 0.5
WEB_URL = "http://localhost:3000"
COMMAND = (sys.executable, "-m", "dema")


def register(commands: Subparsers) -> None:
    demo = commands.add_parser("demo", help="run the whole pipeline and one count")
    demo.add_argument("--sections", type=int, default=5_000)
    demo.add_argument("--speed", type=float, default=600.0)
    demo.add_argument("--seed", type=int)
    demo.add_argument("--workers", type=int, default=2)
    demo.add_argument("--port", type=int, default=8000)
    demo.set_defaults(handler=_demo)


def _demo(args: argparse.Namespace) -> None:
    settings = get_settings()
    signal.signal(signal.SIGTERM, interrupt)
    env, generated = demo_environment(os.environ, settings.signing_key is not None)
    if generated:
        print(
            "warning: DEMA_SIGNING_KEY is not set; using an ephemeral demo key",
            flush=True,
        )
    sections = prepare_database(
        str(settings.database_url), settings.year, args.sections
    )
    print(f"sections: {sections:,}", flush=True)
    supervisor = Supervisor(env)
    supervisor.start("director", [*COMMAND, "director", "run"])
    for index in range(args.workers):
        name = f"demo-{index}"
        supervisor.start(name, [*COMMAND, "workers", "run", "--name", name])
    supervisor.start("api", [*COMMAND, "api", "serve", "--port", str(args.port)])
    base_url = f"http://127.0.0.1:{args.port}"
    signalled = False
    try:
        wait_until_ready(
            [
                lambda: api_healthy(base_url),
                lambda: director_listening(str(settings.redis_url)),
            ],
            supervisor.exited,
            READY_TIMEOUT_SECONDS,
        )
        run = request_count(base_url, args.seed, args.speed)
        print(
            f"counting run #{run['id']} (seed {run['seed']}) at {WEB_URL}", flush=True
        )
        print("press Ctrl+C to stop", flush=True)
        print(f"{watch(supervisor.exited)} stopped; shutting down", flush=True)
    except KeyboardInterrupt:
        print("stopping", flush=True)
        signalled = True
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        supervisor.stop(signalled)


def interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def watch(
    exited: Callable[[], str | None], sleep: Callable[[float], None] = time.sleep
) -> str:
    while (name := exited()) is None:
        sleep(WATCH_SECONDS)
    return name
