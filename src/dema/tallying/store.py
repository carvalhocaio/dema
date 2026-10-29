from collections.abc import Sequence
from typing import Protocol

from dema.domain.ballot import Ballot
from dema.tallying.tally import Tally


class TallyStore(Protocol):
    def add(self, ballot: Ballot) -> bool: ...

    def snapshot(self) -> Tally: ...


class AsyncTallyStore(Protocol):
    async def add_many(self, ballots: Sequence[Ballot]) -> int: ...

    async def snapshot(self) -> Tally: ...
