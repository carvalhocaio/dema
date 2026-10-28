from dataclasses import replace

import pytest

from dema.integrity.codec import decode_ballot, encode_ballot
from dema.integrity.signer import BallotSigner, InvalidSignatureError
from tests.factories import make_ballot

KEY = b"clancy-is-watching-from-the-trench"


def test_codec_round_trips_ballot() -> None:
    ballot = make_ballot()

    assert decode_ballot(encode_ballot(ballot)) == ballot


def test_codec_is_canonical() -> None:
    ballot = make_ballot()

    assert encode_ballot(ballot) == encode_ballot(decode_ballot(encode_ballot(ballot)))


def test_verifies_signed_ballot() -> None:
    signer = BallotSigner(KEY)
    ballot = make_ballot()

    assert signer.verify(signer.sign(ballot)) == ballot


def test_detects_tampered_payload() -> None:
    signer = BallotSigner(KEY)
    signed = signer.sign(make_ballot())
    tampered = replace(signed, payload=signed.payload.replace(b'"99":150', b'"99":999'))

    with pytest.raises(InvalidSignatureError):
        signer.verify(tampered)


def test_rejects_ballot_signed_with_another_key() -> None:
    forged = BallotSigner(b"x" * 32).sign(make_ballot())

    with pytest.raises(InvalidSignatureError):
        BallotSigner(KEY).verify(forged)


def test_rejects_short_keys() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        BallotSigner(b"short")
