from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from dema.domain.ballot import Ballot
from dema.domain.election import Election
from dema.tallying.outcome import Outcome, decide
from dema.tallying.store import TallyStore
from dema.tallying.tally import Tally


@dataclass(frozen=True, slots=True)
class Frame:
    tally: Tally
    outcome: Outcome


def replay(
    ballots: Iterable[Ballot], store: TallyStore, election: Election
) -> Iterator[Frame]:
    for ballot in ballots:
        if store.add(ballot):
            tally = store.snapshot()
            yield Frame(tally=tally, outcome=decide(election, tally))
