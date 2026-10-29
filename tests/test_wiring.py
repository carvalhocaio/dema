import pytest
from pydantic import SecretStr

from dema.config import Settings
from dema.wiring import MissingSigningKeyError, build_signer
from tests.factories import make_ballot
from tests.helpers import SIGNING_KEY


def test_requires_signing_key() -> None:
    with pytest.raises(MissingSigningKeyError, match="DEMA_SIGNING_KEY"):
        build_signer(Settings(signing_key=None))


def test_builds_signer_from_settings() -> None:
    signer = build_signer(Settings(signing_key=SecretStr(SIGNING_KEY.decode())))

    assert signer.verify(signer.sign(make_ballot())).ballot == make_ballot()
