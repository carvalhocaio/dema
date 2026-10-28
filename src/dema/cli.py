import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from dema.domain.election import ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.sections.source import SectionSource
from dema.sections.synthetic import SyntheticSectionSource
from dema.sections.tse import TseSectionSource

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
    return parser


def _import_tse(args: argparse.Namespace) -> None:
    _persist(TseSectionSource(args.csv, ElectionRound(args.round)), args.output)


def _synthesize(args: argparse.Namespace) -> None:
    _persist(SyntheticSectionSource(args.count, seed=args.seed), args.output)


def _summarize(args: argparse.Namespace) -> None:
    _print_summary(SectionCatalog.from_parquet(args.catalog))


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
