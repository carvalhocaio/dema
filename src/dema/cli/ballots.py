import argparse
import asyncio
from pathlib import Path

from dema.cli.common import Subparsers, format_leaders
from dema.config import get_settings
from dema.domain.election import Election, ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.diagnostics import Checkpoint, counting_timeline
from dema.simulation.generator import BallotGenerator
from dema.simulation.runoff import RunoffGenerator
from dema.simulation.sampler import ScenarioSampler
from dema.simulation.scenario import Scenario
from dema.streaming.publisher import BallotPublisher
from dema.streaming.stream import BallotStream
from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.outcome import Verdict
from dema.tallying.replay import replay
from dema.wiring import (
    REFERENCE_SCENARIO,
    build_signer,
    load_active_election,
    open_database,
    open_redis,
)

SAMPLED = "sampled"
REFERENCE = "reference"


def register(commands: Subparsers) -> None:
    ballots = commands.add_parser("ballots", help="simulate ballot reports")
    actions = ballots.add_subparsers(required=True)

    simulate = actions.add_parser("simulate", help="generate ballot reports")
    simulate.add_argument("catalog", type=Path)
    simulate.add_argument("output", type=Path)
    simulate.add_argument("--seed", type=int, default=2026)
    simulate.add_argument(
        "--scenario",
        choices=(SAMPLED, REFERENCE),
        default=SAMPLED,
        help="draw national and regional swings from the seed, or use the reference",
    )
    simulate.set_defaults(handler=_simulate)

    tally = actions.add_parser("tally", help="replay ballots into a tally")
    tally.add_argument("ballots", type=Path)
    tally.add_argument("--steps", type=int, default=10)
    tally.add_argument("--round", type=int, choices=[1, 2], default=1)
    tally.set_defaults(handler=_tally)

    runoff = actions.add_parser("runoff", help="derive second-round ballots")
    runoff.add_argument("first_round", type=Path)
    runoff.add_argument("output", type=Path)
    runoff.add_argument("--seed", type=int, default=2026)
    runoff.set_defaults(handler=_runoff)

    publish = actions.add_parser("publish", help="stream signed ballots to Redis")
    publish.add_argument("ballots", type=Path)
    publish.add_argument("--speed", type=float, help="overrides DEMA_SPEED_FACTOR")
    publish.set_defaults(handler=_publish)


def _simulate(args: argparse.Namespace) -> None:
    catalog = SectionCatalog.from_parquet(args.catalog)
    scenario = _scenario(args.scenario, args.seed)
    ballots = BallotGenerator(scenario, seed=args.seed).generate(catalog)
    ballots.to_parquet(args.output)
    print(f"ballots: {len(ballots):,}")
    for checkpoint in counting_timeline(ballots):
        print(_format_checkpoint(checkpoint))


def _scenario(kind: str, seed: int) -> Scenario:
    if kind == REFERENCE:
        return REFERENCE_SCENARIO
    draw = ScenarioSampler(REFERENCE_SCENARIO).draw(seed)
    print(f"national strength (seed {seed}):")
    for candidate in REFERENCE_SCENARIO.election.candidates:
        print(f"  {candidate.name:<10}{draw.national[candidate.number]:>8.2%}")
    return draw.scenario


def _tally(args: argparse.Namespace) -> None:
    ballots = SimulatedBallots.from_parquet(args.ballots)
    election = ballots_election(ballots, ElectionRound(args.round))
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


def _runoff(args: argparse.Namespace) -> None:
    first_round = SimulatedBallots.from_parquet(args.first_round)
    election = ballots_election(first_round, ElectionRound.FIRST)
    runoff = RunoffGenerator(REFERENCE_SCENARIO, seed=args.seed).generate(
        first_round, election
    )
    runoff.ballots.to_parquet(args.output)
    first, second = runoff.election.candidates
    print(f"first round: {format_leaders(runoff.first_round)}  [runoff]")
    print(f"runoff: {first.name} x {second.name} (seed {args.seed})")
    print(f"ballots: {len(runoff.ballots):,}")
    for checkpoint in counting_timeline(runoff.ballots):
        print(_format_checkpoint(checkpoint))


def _publish(args: argparse.Namespace) -> None:
    published = asyncio.run(_publish_async(args.ballots, args.speed))
    print(f"published {published:,} ballots")


async def _publish_async(path: Path, speed: float | None) -> int:
    settings = get_settings()
    signer = build_signer(settings)
    ballots = SimulatedBallots.from_parquet(path)
    async with open_database(settings) as connection, open_redis(settings) as redis:
        record = await load_active_election(settings, connection)
        stream = BallotStream(redis, record.keys)
        await stream.ensure_group()
        publisher = BallotPublisher(
            stream,
            signer,
            speed_factor=speed or settings.speed_factor,
            batch_size=settings.batch_size,
        )
        return await publisher.publish(ballots.in_release_order(), record.polls_close)


def ballots_election(ballots: SimulatedBallots, round_: ElectionRound) -> Election:
    reference = REFERENCE_SCENARIO.election
    return Election(
        year=reference.year,
        round=round_,
        candidates=tuple(reference.candidate(n) for n in ballots.candidate_numbers),
    )


def _format_checkpoint(checkpoint: Checkpoint) -> str:
    election = REFERENCE_SCENARIO.election
    ranking = sorted(checkpoint.shares.items(), key=lambda item: item[1], reverse=True)
    leaders = "  ".join(
        f"{election.candidate(number).name} {share:.2%}"
        for number, share in ranking[:2]
    )
    return f"  {checkpoint.progress:6.1%}  {leaders}"
