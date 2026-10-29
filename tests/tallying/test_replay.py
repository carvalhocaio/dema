from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.outcome import Verdict
from dema.tallying.replay import replay
from tests.factories import KEONS, LISDEN, NICO, make_ballot, make_election


def test_yields_one_frame_per_new_section() -> None:
    election = make_election()
    store = InMemoryTallyStore(election, total_sections=2, total_electorate=800)
    ballots = [
        make_ballot(section_number=1),
        make_ballot(section_number=1),
        make_ballot(
            nominal_votes={NICO.number: 100, KEONS.number: 120, LISDEN.number: 100},
            section_number=2,
        ),
    ]

    frames = list(replay(ballots, store, election))

    assert [frame.tally.counted_sections for frame in frames] == [1, 2]
    assert frames[0].outcome.verdict is Verdict.UNDECIDED
    assert frames[-1].outcome.verdict is Verdict.RUNOFF
    assert frames[-1].outcome.finalists == (NICO, KEONS)
