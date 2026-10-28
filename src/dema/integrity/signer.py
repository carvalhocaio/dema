import hashlib
import hmac
from dataclasses import dataclass

from dema.domain.ballot import Ballot
from dema.integrity.codec import decode_ballot, encode_ballot

MIN_KEY_BYTES = 32


class InvalidSignatureError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SignedBallot:
    payload: bytes
    signature: str


class BallotSigner:
    def __init__(self, key: bytes) -> None:
        if len(key) < MIN_KEY_BYTES:
            raise ValueError(f"signing key must have at least {MIN_KEY_BYTES} bytes")
        self._key = key

    def sign(self, ballot: Ballot) -> SignedBallot:
        payload = encode_ballot(ballot)
        return SignedBallot(payload=payload, signature=self._digest(payload))

    def verify(self, signed: SignedBallot) -> Ballot:
        if not hmac.compare_digest(self._digest(signed.payload), signed.signature):
            raise InvalidSignatureError("ballot signature does not match its payload")
        return decode_ballot(signed.payload)

    def _digest(self, payload: bytes) -> str:
        return hmac.new(self._key, payload, hashlib.sha3_256).hexdigest()
