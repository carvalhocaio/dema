import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.domain.section import SectionKey
from dema.integrity.codec import decode_ballot
from dema.integrity.signer import BallotSigner, InvalidSignatureError, SignedBallot
from dema.storage.elections import ElectionRecord
from dema.streaming.stream import BallotStream

REJECTED_LIMIT = 20

StreamEntries = list[tuple[bytes, dict[bytes, bytes]]]

COUNTED_BALLOT = """
SELECT payload, signature, received_at
FROM ballots
WHERE run_id = %s AND section = %s
"""

RANDOM_BALLOT = """
SELECT payload, signature, received_at
FROM ballots
WHERE run_id = %(run_id)s AND section = (
    SELECT section FROM ballots WHERE run_id = %(run_id)s
    ORDER BY random() LIMIT 1
)
"""

UNCOUNTED_SECTION = """
SELECT s.key
FROM sections AS s
WHERE NOT EXISTS (
    SELECT FROM ballots AS b WHERE b.run_id = %s AND b.section = s.key
)
ORDER BY random()
LIMIT 1
"""


class NothingToTamperError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AuditedBallot:
    ballot: Ballot
    signature: str
    received_at: datetime
    verified: bool | None


@dataclass(frozen=True, slots=True)
class Rejection:
    entry: str
    at: datetime
    reason: str
    section: str | None


@dataclass(frozen=True, slots=True)
class TamperedBallot:
    section: str
    source: str


class BallotAudit:
    """Reads counted ballots back, re-checking each signature, and forges
    tampered ones so the workers can be seen rejecting them."""

    def __init__(
        self, connection: AsyncConnection, redis: Redis, signer: BallotSigner | None
    ) -> None:
        self._connection = connection
        self._redis = redis
        self._signer = signer

    async def section(
        self, record: ElectionRecord, key: SectionKey
    ) -> AuditedBallot | None:
        cursor = await self._connection.execute(
            COUNTED_BALLOT, (record.run.id, str(key))
        )
        return self._audited(await cursor.fetchone())

    async def random_section(self, record: ElectionRecord) -> AuditedBallot | None:
        cursor = await self._connection.execute(
            RANDOM_BALLOT, {"run_id": record.run.id}
        )
        return self._audited(await cursor.fetchone())

    async def rejected(
        self, record: ElectionRecord, limit: int = REJECTED_LIMIT
    ) -> tuple[Rejection, ...]:
        entries = await self._redis.xrevrange(record.keys.rejected, count=limit)
        return tuple(
            _rejection(entry_id, fields)
            for entry_id, fields in cast(StreamEntries, entries)
        )

    async def tamper(self, record: ElectionRecord) -> TamperedBallot:
        cursor = await self._connection.execute(
            RANDOM_BALLOT, {"run_id": record.run.id}
        )
        source = await cursor.fetchone()
        cursor = await self._connection.execute(UNCOUNTED_SECTION, (record.run.id,))
        target = await cursor.fetchone()
        if source is None or target is None:
            raise NothingToTamperError
        payload, signature, _ = source
        document = json.loads(payload)
        original = document["section"]
        forged = forge(document, target[0])
        stream = BallotStream(self._redis, record.keys, run_id=record.run.id)
        await stream.publish([SignedBallot(payload=forged, signature=signature)])
        return TamperedBallot(section=target[0], source=original)

    def _audited(self, row: tuple[bytes, str, datetime] | None) -> AuditedBallot | None:
        if row is None:
            return None
        payload, signature, received_at = row
        return AuditedBallot(
            ballot=decode_ballot(payload),
            signature=signature,
            received_at=received_at,
            verified=self._verify(SignedBallot(payload=payload, signature=signature)),
        )

    def _verify(self, signed: SignedBallot) -> bool | None:
        if self._signer is None:
            return None
        try:
            self._signer.verify(signed)
        except InvalidSignatureError:
            return False
        return True


def forge(document: dict[str, Any], section: str) -> bytes:
    """Moves a signed ballot to another section and swaps its two most voted
    candidates, keeping the payload's canonical encoding."""
    votes: dict[str, int] = document["nominal_votes"]
    first, second = sorted(votes, key=lambda number: votes[number], reverse=True)[:2]
    swapped = votes | {first: votes[second], second: votes[first]}
    tampered = document | {"section": section, "nominal_votes": swapped}
    return json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode()


def _rejection(entry_id: bytes, fields: dict[bytes, bytes]) -> Rejection:
    milliseconds = int(entry_id.split(b"-")[0])
    return Rejection(
        entry=entry_id.decode(),
        at=datetime.fromtimestamp(milliseconds / 1000, UTC),
        reason=fields[b"reason"].decode(),
        section=_readable_section(fields.get(b"payload")),
    )


def _readable_section(payload: bytes | None) -> str | None:
    if payload is None:
        return None
    try:
        section = json.loads(payload)["section"]
    except (ValueError, KeyError, TypeError):
        return None
    return section if isinstance(section, str) else None
