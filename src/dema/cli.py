import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from dema.domain.election import ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.sections.source import SectionSource
from dema.sections.synthetic import SyntheticSectionSource
from dema.sections.tse import TseSectionSource
from dema.simulation.diagnostics import Checkpoint, counting_timeline
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND

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
