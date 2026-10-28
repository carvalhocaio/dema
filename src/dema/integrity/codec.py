import json
from datetime import datetime

from dema.domain.ballot import Ballot
from dema.domain.section import SectionKey


def encode_ballot(ballot: Ballot) -> bytes:
    document = {
        "section": str(ballot.section),
        "eligible_voters": ballot.eligible_voters,
        "nominal_votes": {str(n): v for n, v in ballot.nominal_votes.items()},
        "blank_votes": ballot.blank_votes,
        "null_votes": ballot.null_votes,
        "issued_at": ballot.issued_at.isoformat(),
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def decode_ballot(payload: bytes) -> Ballot:
    document = json.loads(payload)
    return Ballot(
        section=SectionKey.parse(document["section"]),
        eligible_voters=document["eligible_voters"],
        nominal_votes={int(n): v for n, v in document["nominal_votes"].items()},
        blank_votes=document["blank_votes"],
        null_votes=document["null_votes"],
        issued_at=datetime.fromisoformat(document["issued_at"]),
    )
