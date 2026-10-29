import argparse

from dema.tallying.outcome import Outcome
from dema.tallying.tally import Tally

Subparsers = argparse._SubParsersAction  # pyright: ignore[reportPrivateUsage]


def format_leaders(outcome: Outcome, top: int = 2) -> str:
    return "  ".join(
        f"{result.candidate.name} {result.share:.2%}"
        for result in outcome.ranking[:top]
    )


def format_progress(tally: Tally, outcome: Outcome) -> str:
    return f"  {tally.progress:6.1%}  {format_leaders(outcome)}  [{outcome.verdict}]"
