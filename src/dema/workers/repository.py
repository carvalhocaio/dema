from collections.abc import Sequence
from typing import Protocol

from dema.integrity.signer import VerifiedBallot


class BallotRepository(Protocol):
    async def save_many(self, verified: Sequence[VerifiedBallot]) -> int: ...
