import argparse
import asyncio
from pathlib import Path

from dema.cli.common import Subparsers, format_leaders
from dema.config import get_settings
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.diagnostics import Checkpoint, counting_timeline
from dema.simulation.generator import BallotGenerator
from dema.streaming.publisher import BallotPublisher
from dema.streaming.stream import BallotStream
from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.outcome import Verdict
from dema.tallying.replay import replay
from dema.wiring import ACTIVE_KEYS, ACTIVE_SCENARIO, build_signer, open_redis


def register(commands: Subparsers) -> None:
    ballots = commands.add_parser("ballots", help="simulate ballot reports")
    actions = ballots.add_subparsers(required=True)

    simulate = actions.add_parser("simulate", help="generate ballot reports")
    simulate.add_argument("catalog", type=Path)
    simulate.add_argument("output", type=Path)
    simulate.add_argument("--seed", type=int, default=2026)
    simulate.set_defaults(handler=_simulate)

    tally = actions.add_parser("tally", help="replay ballots into a tally")
    tally.add_argument("ballots", type=Path)
    tally.add_argument("--steps", type=int, default=10)
    tally.set_defaults(handler=_tally)

    publish = actions.add_parser("publish", help="stream signed ballots to Redis")
    publish.add_argument("ballots", type=Path)
    publish.add_argument("--speed", type=float, help="overrides DEMA_SPEED_FACTOR")
    publish.set_defaults(handler=_publish)


def _simulate(args: argparse.Namespace) -> None:
    catalog = SectionCatalog.from_parquet(args.catalog)
    ballots = BallotGenerator(ACTIVE_SCENARIO, seed=args.seed).generate(catalog)
    ballots.to_parquet(args.output)
    print(f"ballots: {len(ballots):,}")
    for checkpoint in counting_timeline(ballots):
        print(_format_checkpoint(checkpoint))


def _tally(args: argparse.Namespace) -> None:
    ballots = SimulatedBallots.from_parquet(args.ballots)
    election = ACTIVE_SCENARIO.election
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
            names = " x ".join(c.name for c in frame.outcome.finalists)
            print(f"  >> {verdict} at {frame.tally.progress:.2%}: {names}")
        if frame.tally.progress >= next_step / args.steps:
            next_step += 1
            print(f"  {frame.tally.progress:6.1%}  {format_leaders(frame.outcome)}")


def _publish(args: argparse.Namespace) -> None:
    published = asyncio.run(_publish_async(args.ballots, args.speed))
    print(f"published {published:,} ballots")


async def _publish_async(path: Path, speed: float | None) -> int:
    settings = get_settings()
    signer = build_signer(settings)
    ballots = SimulatedBallots.from_parquet(path)
    async with open_redis(settings) as redis:
        stream = BallotStream(redis, ACTIVE_KEYS)
        await stream.ensure_group()
        publisher = BallotPublisher(
            stream,
            signer,
            speed_factor=speed or settings.speed_factor,
            batch_size=settings.batch_size,
        )
        return await publisher.publish(
            ballots.in_release_order(), ACTIVE_SCENARIO.polls_close
        )


def _format_checkpoint(checkpoint: Checkpoint) -> str:
    election = ACTIVE_SCENARIO.election
    ranking = sorted(checkpoint.shares.items(), key=lambda item: item[1], reverse=True)
    leaders = "  ".join(
        f"{election.candidate(number).name} {share:.2%}"
        for number, share in ranking[:2]
    )
    return f"  {checkpoint.progress:6.1%}  {leaders}"
