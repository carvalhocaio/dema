import json

import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.audit.ballots import BallotAudit, NothingToTamperError, forge
from dema.domain.ballot import Ballot
from dema.domain.run import Run
from dema.domain.section import SectionKey
from dema.integrity.codec import decode_ballot
from dema.integrity.signer import BallotSigner, InvalidSignatureError, SignedBallot
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.elections import ElectionRecord
from dema.streaming.stream import BallotStream, StreamEntry
from tests.helpers import SIGNING_KEY
from tests.storage.test_ballots import verify_all

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election


@pytest.fixture
def record(first_run: Run) -> ElectionRecord:
    return ElectionRecord(ELECTION, DEMA_2026_FIRST_ROUND.polls_close, first_run)


@pytest.fixture
def signer() -> BallotSigner:
    return BallotSigner(SIGNING_KEY)


async def count(
    connection: AsyncConnection, record: ElectionRecord, ballots: list[Ballot]
) -> None:
    repository = PostgresBallotRepository(connection, ELECTION, record.run.id)
    await repository.save_many(verify_all(ballots))


async def test_reads_a_counted_ballot_back_and_rechecks_its_signature(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    signer: BallotSigner,
    small_ballots: list[Ballot],
) -> None:
    ballot = small_ballots[0]
    await count(async_connection, record, [ballot])
    audit = BallotAudit(async_connection, redis_client, signer)

    audited = await audit.section(record, ballot.section)

    assert audited is not None
    assert audited.ballot == ballot
    assert audited.signature == signer.sign(ballot).signature
    assert audited.verified is True


async def test_reports_whether_the_signature_could_be_checked(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    small_ballots: list[Ballot],
) -> None:
    ballot = small_ballots[0]
    await count(async_connection, record, [ballot])
    other_key = BallotSigner(b"x" * 32)

    keyless = await BallotAudit(async_connection, redis_client, None).section(
        record, ballot.section
    )
    wrong = await BallotAudit(async_connection, redis_client, other_key).section(
        record, ballot.section
    )

    assert keyless is not None and keyless.verified is None
    assert wrong is not None and wrong.verified is False


async def test_finds_nothing_for_sections_still_to_count(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    small_ballots: list[Ballot],
) -> None:
    audit = BallotAudit(async_connection, redis_client, None)

    assert await audit.section(record, small_ballots[0].section) is None
    assert await audit.random_section(record) is None


async def test_draws_one_of_the_counted_sections(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    small_ballots: list[Ballot],
) -> None:
    counted = small_ballots[:3]
    await count(async_connection, record, counted)
    audit = BallotAudit(async_connection, redis_client, None)

    drawn = await audit.random_section(record)

    assert drawn is not None
    assert drawn.ballot in counted


async def test_lists_the_latest_rejections_with_readable_sections(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    small_ballots: list[Ballot],
) -> None:
    stream = BallotStream(redis_client, record.keys)
    signed = BallotSigner(SIGNING_KEY).sign(small_ballots[0])
    await stream.reject(StreamEntry(b"1-0", signed), "invalid signature")
    await stream.reject(StreamEntry(b"2-0", None), "malformed entry")
    await stream.reject(
        StreamEntry(b"3-0", SignedBallot(b"not json", "00")), "invalid payload"
    )
    await stream.reject(
        StreamEntry(b"4-0", SignedBallot(b'{"section": 7}', "00")), "invalid payload"
    )
    audit = BallotAudit(async_connection, redis_client, None)

    rejections = await audit.rejected(record)

    assert [r.section for r in rejections] == [
        None,
        None,
        None,
        str(small_ballots[0].section),
    ]
    assert rejections[-1].reason == "invalid signature"
    assert rejections[0].at.year >= 2026
    assert await audit.rejected(record, limit=1) == rejections[:1]


async def test_tampers_with_a_section_still_to_count(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
    signer: BallotSigner,
    small_ballots: list[Ballot],
) -> None:
    source = small_ballots[0]
    await count(async_connection, record, [source])
    stream = BallotStream(redis_client, record.keys)
    await stream.ensure_group()
    audit = BallotAudit(async_connection, redis_client, signer)

    tampered = await audit.tamper(record)

    [entry] = await stream.read("auditor", 10, 10)
    assert entry.run_id == record.run.id
    assert entry.signed is not None
    assert entry.signed.signature == signer.sign(source).signature
    assert tampered.source == str(source.section)
    assert decode_ballot(entry.signed.payload).section == SectionKey.parse(
        tampered.section
    )
    assert await audit.section(record, SectionKey.parse(tampered.section)) is None
    with pytest.raises(InvalidSignatureError):
        signer.verify(entry.signed)


async def test_cannot_tamper_before_any_section_is_counted(
    async_connection: AsyncConnection,
    redis_client: Redis,
    record: ElectionRecord,
) -> None:
    audit = BallotAudit(async_connection, redis_client, None)

    with pytest.raises(NothingToTamperError):
        await audit.tamper(record)


def test_forging_moves_the_ballot_and_swaps_the_two_leaders() -> None:
    document = {
        "section": "SP-71072-0001-0001",
        "nominal_votes": {"27": 90, "99": 40, "31": 10},
        "blank_votes": 1,
    }

    forged = json.loads(forge(document, "AC-10025-0001-0002"))

    assert forged["section"] == "AC-10025-0001-0002"
    assert forged["nominal_votes"] == {"27": 40, "99": 90, "31": 10}
    assert forged["blank_votes"] == 1
