import argparse
from collections.abc import Callable, Sequence

from dema.cli import (
    api,
    ballots,
    database,
    director,
    election,
    sections,
    tally,
    workers,
)
from dema.cli.election import SetupError
from dema.domain.election import ElectionNotSetUpError
from dema.simulation.runoff import NoRunoffError
from dema.wiring import MissingSigningKeyError

Handler = Callable[[argparse.Namespace], None]
COMMANDS = (sections, ballots, database, election, workers, tally, api, director)
EXPECTED_ERRORS = (
    ElectionNotSetUpError,
    MissingSigningKeyError,
    NoRunoffError,
    SetupError,
)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dema")
    commands = parser.add_subparsers(required=True)
    for command in COMMANDS:
        command.register(commands)
    args = parser.parse_args(argv)
    handler: Handler = args.handler
    try:
        handler(args)
    except EXPECTED_ERRORS as error:
        raise SystemExit(f"dema: {error}") from error
