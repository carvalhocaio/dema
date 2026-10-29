import argparse
from collections.abc import Callable, Sequence

from dema.cli import ballots, database, election, sections, tally, workers
from dema.tallying.redis_store import ElectionNotSetUpError
from dema.wiring import MissingSigningKeyError

Handler = Callable[[argparse.Namespace], None]
COMMANDS = (sections, ballots, database, election, workers, tally)
EXPECTED_ERRORS = (ElectionNotSetUpError, MissingSigningKeyError)


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
