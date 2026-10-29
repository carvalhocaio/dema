from collections.abc import Sequence
from datetime import timedelta

import pytest

from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner, SignedBallot
from dema.simulation.presets import FIRST_ROUND_POLLS_CLOSE
from dema.streaming.publisher import BallotPublisher
from tests.factories import make_ballot
from tests.helpers import SIGNING_KEY


class RecordingSink:
    def __init__(self) -> None:
        self.batches: list[list[SignedBallot]] = []

    async def publish(self, ballots: Sequence[SignedBallot]) -> int:
        self.batches.append(list(ballots))
        return len(ballots)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def ballot_released_after(minutes: float, section: int) -> Ballot:
    ballot = make_ballot(section_number=section)
    issued_at = FIRST_ROUND_POLLS_CLOSE + timedelta(minutes=minutes)
    return Ballot(
        section=ballot.section,
        eligible_voters=ballot.eligible_voters,
        nominal_votes=ballot.nominal_votes,
        blank_votes=ballot.blank_votes,
        null_votes=ballot.null_votes,
        issued_at=issued_at,
    )


def make_publisher(
    sink: RecordingSink,
    clock: FakeClock,
    speed_factor: float = 60,
    batch_size: int = 10,
) -> BallotPublisher:
    return BallotPublisher(
        sink,
        BallotSigner(SIGNING_KEY),
        speed_factor=speed_factor,
        batch_size=batch_size,
        clock=clock,
        sleep=clock.sleep,
    )


async def test_paces_releases_by_speed_factor() -> None:
    sink, clock = RecordingSink(), FakeClock()
    ballots = [ballot_released_after(minutes, i) for i, minutes in enumerate((1, 2), 1)]

    published = await make_publisher(sink, clock).publish(
        ballots, FIRST_ROUND_POLLS_CLOSE
    )

    assert published == 2
    assert clock.sleeps == [1.0, 1.0]
    assert [len(batch) for batch in sink.batches] == [0, 1, 1]


async def test_groups_ballots_due_together_in_batches() -> None:
    sink, clock = RecordingSink(), FakeClock()
    ballots = [ballot_released_after(0, section) for section in range(1, 26)]

    await make_publisher(sink, clock).publish(ballots, FIRST_ROUND_POLLS_CLOSE)

    assert clock.sleeps == []
    assert [len(batch) for batch in sink.batches] == [10, 10, 5]


async def test_signs_every_ballot() -> None:
    sink, clock = RecordingSink(), FakeClock()
    signer = BallotSigner(SIGNING_KEY)
    ballot = ballot_released_after(0, 1)

    await make_publisher(sink, clock).publish([ballot], FIRST_ROUND_POLLS_CLOSE)

    [[signed]] = [batch for batch in sink.batches if batch]
    assert signer.verify(signed).ballot == ballot


def test_rejects_non_positive_speed() -> None:
    with pytest.raises(ValueError, match="positive"):
        make_publisher(RecordingSink(), FakeClock(), speed_factor=0)
