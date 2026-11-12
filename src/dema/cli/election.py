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
from dema.domain.run import Run
from dema.runtime.active import ActiveRuns
from dema.sections.catalog import SectionCatalog
from dema.services.counting import REFERENCE_SCENARIO
from dema.services.runs import start_run
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.seed import replace_sections, seed_election
from dema.wiring import open_database, open_redis

RUNOFF_CANDIDATES = 2


class SetupError(ValueError):
    pass


def register(commands: Subparsers) -> None:
    election = commands.add_parser("election", help="prepare an election run")
    actions = election.add_subparsers(required=True)
    setup = actions.add_parser("setup", help="seed sections and open a new run")
    setup.add_argument("catalog", type=Path)
    setup.add_argument("--round", type=int, choices=[1, 2], default=1)
    setup.add_argument(
        "--ballots", type=Path, help="second-round ballots naming the finalists"
    )
    setup.add_argument("--seed", type=int, default=0, help="recorded with the run")
    setup.set_defaults(handler=_setup)


def _setup(args: argparse.Namespace) -> None:
    settings = get_settings()
    round_ = ElectionRound(args.round)
    finalists = _finalist_numbers(round_, args.ballots)
    catalog = SectionCatalog.from_parquet(args.catalog)
    run = asyncio.run(_open_run(settings, round_, finalists, catalog, args.seed))
    print(f"election {run.year}/{run.round} ready (run #{run.id})")
    print(f"sections:   {len(catalog):>13,}")
    print(f"electorate: {catalog.total_electorate:>13,}")


def _finalist_numbers(round_: ElectionRound, ballots: Path | None) -> tuple[int, ...]:
    if round_ is ElectionRound.FIRST:
        if ballots is not None:
            raise SetupError("--ballots only applies to the second round")
        return ()
    if ballots is None:
        raise SetupError("the second round needs --ballots <ballots-r2.parquet>")
    numbers = SimulatedBallots.from_parquet(ballots).candidate_numbers
    if len(numbers) != RUNOFF_CANDIDATES:
        raise SetupError("second-round ballots must name exactly two candidates")
    return numbers


async def _open_run(
    settings: Settings,
    round_: ElectionRound,
    finalists: tuple[int, ...],
    catalog: SectionCatalog,
    seed: int,
) -> Run:
    async with open_database(settings) as connection, open_redis(settings) as redis:
        active = ActiveRuns(redis, connection)
        parent = await _parent(active, round_)
        election, polls_close = await _election(active, settings, parent, finalists)
        await asyncio.to_thread(_seed, settings, election, polls_close, catalog)
        run = await active.runs.create(
            election.year,
            round_,
            seed,
            [candidate.number for candidate in election.candidates],
            parent_id=None if parent is None else parent.id,
        )
        record = await start_run(
            active, redis, run, len(catalog), catalog.total_electorate
        )
    return record.run


async def _parent(active: ActiveRuns, round_: ElectionRound) -> Run | None:
    if round_ is ElectionRound.FIRST:
        return None
    parent = await active.runs.active()
    if parent is None or parent.round is not ElectionRound.FIRST:
        raise SetupError("the second round needs an active first-round run")
    return parent


async def _election(
    active: ActiveRuns,
    settings: Settings,
    parent: Run | None,
    finalists: tuple[int, ...],
) -> tuple[Election, datetime]:
    if parent is None:
        election = replace(REFERENCE_SCENARIO.election, year=settings.year)
        return election, REFERENCE_SCENARIO.polls_close
    first_round = (await active.record(parent.id)).election
    candidates = tuple(_finalist(first_round, number) for number in finalists)
    election = Election(
        year=parent.year, round=ElectionRound.SECOND, candidates=candidates
    )
    return election, SECOND_ROUND_POLLS_CLOSE


def _finalist(first_round: Election, number: int) -> Candidate:
    if number not in first_round.candidate_numbers:
        raise SetupError(f"candidate {number} did not run in the first round")
    return first_round.candidate(number)


def _seed(
    settings: Settings,
    election: Election,
    polls_close: datetime,
    catalog: SectionCatalog,
) -> None:
    with psycopg.connect(str(settings.database_url)) as connection:
        seed_election(connection, election, polls_close)
        replace_sections(connection, catalog)
