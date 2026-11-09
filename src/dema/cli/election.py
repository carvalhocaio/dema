import argparse
import asyncio
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import psycopg

from dema.cli.common import Subparsers
from dema.config import Settings, get_settings
from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.elections import ElectionRepository
from dema.storage.seed import clear_ballots, replace_sections, seed_election
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import REFERENCE_SCENARIO, open_database, open_redis

RUNOFF_CANDIDATES = 2


class SetupError(ValueError):
    pass


def register(commands: Subparsers) -> None:
    election = commands.add_parser("election", help="prepare an election run")
    actions = election.add_subparsers(required=True)
    setup = actions.add_parser("setup", help="seed sections and reset the tally")
    setup.add_argument("catalog", type=Path)
    setup.add_argument(
        "--round", type=int, choices=[1, 2], help="defaults to DEMA_ROUND"
    )
    setup.add_argument(
        "--ballots", type=Path, help="second-round ballots naming the finalists"
    )
    setup.set_defaults(handler=_setup)


def _setup(args: argparse.Namespace) -> None:
    settings = get_settings()
    round_ = ElectionRound(args.round or settings.round)
    election, polls_close = _election_for(round_, args.ballots, settings)
    catalog = SectionCatalog.from_parquet(args.catalog)
    with psycopg.connect(str(settings.database_url)) as connection:
        seed_election(connection, election, polls_close)
        clear_ballots(connection, election)
        replace_sections(connection, catalog)
    asyncio.run(_reset_redis(election, catalog))
    names = " x ".join(candidate.name for candidate in election.candidates)
    print(f"election {election.year}/{election.round} ready")
    print(f"candidates: {names}")
    print(f"sections:   {len(catalog):>13,}")
    print(f"electorate: {catalog.total_electorate:>13,}")


def _election_for(
    round_: ElectionRound, ballots: Path | None, settings: Settings
) -> tuple[Election, datetime]:
    if round_ is ElectionRound.FIRST:
        if ballots is not None:
            raise SetupError("--ballots only applies to the second round")
        election = replace(REFERENCE_SCENARIO.election, year=settings.year)
        return election, REFERENCE_SCENARIO.polls_close
    if ballots is None:
        raise SetupError("the second round needs --ballots <ballots-r2.parquet>")
    numbers = SimulatedBallots.from_parquet(ballots).candidate_numbers
    if len(numbers) != RUNOFF_CANDIDATES:
        raise SetupError("second-round ballots must name exactly two candidates")
    first_round = asyncio.run(_first_round(settings))
    candidates = tuple(_finalist(first_round, number) for number in numbers)
    election = Election(year=settings.year, round=round_, candidates=candidates)
    return election, SECOND_ROUND_POLLS_CLOSE


def _finalist(first_round: Election, number: int) -> Candidate:
    if number not in first_round.candidate_numbers:
        raise SetupError(f"candidate {number} did not run in the first round")
    return first_round.candidate(number)


async def _first_round(settings: Settings) -> Election:
    async with open_database(settings) as connection:
        record = await ElectionRepository(connection).load(
            settings.year, ElectionRound.FIRST
        )
    return record.election


async def _reset_redis(election: Election, catalog: SectionCatalog) -> None:
    async with open_redis(get_settings()) as redis:
        keys = ElectionKeys.for_election(election)
        await BallotStream(redis, keys).clear()
        store = RedisTallyStore(redis, keys, election)
        await store.reset(len(catalog), catalog.total_electorate)
