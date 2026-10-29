from typing import Protocol

from dema.domain.ballot import Ballot
from dema.tallying.tally import Tally


class TallyStore(Protocol):
    def add(self, ballot: Ballot) -> bool: ...

    def snapshot(self) -> Tally: ...
