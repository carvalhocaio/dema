import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

import psycopg

from dema.config import get_settings
from dema.domain.election import ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.sections.source import SectionSource
from dema.sections.synthetic import SyntheticSectionSource
from dema.sections.tse import TseSectionSource
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.diagnostics import Checkpoint, counting_timeline
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.migrator import Migrator
from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.outcome import Outcome, Verdict
from dema.tallying.replay import Frame, replay

Handler = Callable[[argparse.Namespace], None]


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    handler: Handler = args.handler
    handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dema")
    commands = parser.add_subparsers(required=True)
    sections = commands.add_parser("sections", help="manage the section catalog")
    actions = sections.add_subparsers(required=True)

    import_ = actions.add_parser("import", help="build catalog from a TSE CSV")
    import_.add_argument("csv", type=Path)
    import_.add_argument("output", type=Path)
    import_.add_argument("--round", type=int, choices=[1, 2], default=1)
    import_.set_defaults(handler=_import_tse)

    synth = actions.add_parser("synth", help="build a synthetic catalog")
    synth.add_argument("count", type=int)
    synth.add_argument("output", type=Path)
    synth.add_argument("--seed", type=int, default=2026)
    synth.set_defaults(handler=_synthesize)

    summary = actions.add_parser("summary", help="describe a stored catalog")
    summary.add_argument("catalog", type=Path)
    summary.set_defaults(handler=_summarize)

    ballots = commands.add_parser("ballots", help="simulate ballot reports")
    ballot_actions = ballots.add_subparsers(required=True)
    simulate = ballot_actions.add_parser("simulate", help="generate ballot reports")
    simulate.add_argument("catalog", type=Path)
    simulate.add_argument("output", type=Path)
    simulate.add_argument("--seed", type=int, default=2026)
    simulate.set_defaults(handler=_simulate)

    tally = ballot_actions.add_parser("tally", help="replay ballots into a tally")
    tally.add_argument("ballots", type=Path)
    tally.add_argument("--steps", type=int, default=10)
    tally.set_defaults(handler=_tally)

    database = commands.add_parser("db", help="manage the database")
    database_actions = database.add_subparsers(required=True)
    migrate = database_actions.add_parser("migrate", help="apply pending migrations")
    migrate.set_defaults(handler=_migrate)
    return parser


def _import_tse(args: argparse.Namespace) -> None:
    _persist(TseSectionSource(args.csv, ElectionRound(args.round)), args.output)


def _synthesize(args: argparse.Namespace) -> None:
    _persist(SyntheticSectionSource(args.count, seed=args.seed), args.output)


def _summarize(args: argparse.Namespace) -> None:
    _print_summary(SectionCatalog.from_parquet(args.catalog))


def _simulate(args: argparse.Namespace) -> None:
    catalog = SectionCatalog.from_parquet(args.catalog)
    ballots = BallotGenerator(DEMA_2026_FIRST_ROUND, seed=args.seed).generate(catalog)
    ballots.to_parquet(args.output)
    print(f"ballots: {len(ballots):,}")
    for checkpoint in counting_timeline(ballots):
        print(_format_checkpoint(checkpoint))


def _tally(args: argparse.Namespace) -> None:
    ballots = SimulatedBallots.from_parquet(args.ballots)
    election = DEMA_2026_FIRST_ROUND.election
    store = InMemoryTallyStore(
        election,
        total_sections=len(ballots),
        total_electorate=int(ballots.frame["eligible_voters"].sum()),
    )
    next_step = 1
    verdict = Verdict.UNDECIDED
    for frame in replay(ballots.in_release_order(), store, election):
        if frame.outcome.verdict is not verdict:
            verdict = frame.outcome.verdict
            print(f"  >> {_format_verdict(frame)}")
        if frame.tally.progress >= next_step / args.steps:
            next_step += 1
            print(f"  {frame.tally.progress:6.1%}  {_format_leaders(frame.outcome)}")


def _migrate(_: argparse.Namespace) -> None:
    with psycopg.connect(str(get_settings().database_url)) as connection:
        applied = Migrator(connection).migrate()
    for version in applied:
        print(f"applied {version}")
    if not applied:
        print("database is up to date")


def _format_verdict(frame: Frame) -> str:
    names = " x ".join(candidate.name for candidate in frame.outcome.finalists)
    return f"{frame.outcome.verdict} at {frame.tally.progress:.2%}: {names}"


def _format_leaders(outcome: Outcome) -> str:
    return "  ".join(
        f"{result.candidate.name} {result.share:.2%}" for result in outcome.ranking[:2]
    )


def _format_checkpoint(checkpoint: Checkpoint) -> str:
    election = DEMA_2026_FIRST_ROUND.election
    ranking = sorted(checkpoint.shares.items(), key=lambda item: item[1], reverse=True)
    leaders = "  ".join(
        f"{election.candidate(number).name} {share:.2%}"
        for number, share in ranking[:2]
    )
    return f"  {checkpoint.progress:6.1%}  {leaders}"


def _persist(source: SectionSource, output: Path) -> None:
    catalog = source.load()
    catalog.to_parquet(output)
    _print_summary(catalog)


def _print_summary(catalog: SectionCatalog) -> None:
    print(f"sections:   {len(catalog):>13,}")
    print(f"electorate: {catalog.total_electorate:>13,}")
    ranking = sorted(
        catalog.electorate_by_state().items(), key=lambda item: item[1], reverse=True
    )
    for state, voters in ranking:
        print(f"  {state}: {voters:>12,}")
