from dema.domain.election import ElectionRound
from dema.tallying.outcome import Verdict, decide
from dema.tallying.tally import Tally
from tests.factories import KEONS, LISDEN, NICO, make_election

FIRST_ROUND = make_election()
SECOND_ROUND = make_election(round_=ElectionRound.SECOND, candidates=(NICO, KEONS))


def make_tally(votes: dict[int, int], remaining: int = 0) -> Tally:
    counted = sum(votes.values())
    return Tally(
        nominal_votes=votes,
        blank_votes=0,
        null_votes=0,
        counted_sections=10 if remaining == 0 else 5,
        counted_electorate=counted,
        total_sections=10,
        total_electorate=counted + remaining,
    )


def first_round(nico: int, keons: int, lisden: int, remaining: int = 0) -> Tally:
    votes = {NICO.number: nico, KEONS.number: keons, LISDEN.number: lisden}
    return make_tally(votes, remaining)


def test_ranks_candidates_by_votes() -> None:
    outcome = decide(FIRST_ROUND, first_round(200, 500, 300))

    assert [r.candidate for r in outcome.ranking] == [KEONS, LISDEN, NICO]
    assert outcome.leader.share == 0.5


def test_elects_with_majority_when_complete() -> None:
    outcome = decide(FIRST_ROUND, first_round(510, 400, 90))

    assert outcome.verdict is Verdict.ELECTED
    assert outcome.finalists == (NICO,)


def test_elects_before_complete_when_majority_is_secured() -> None:
    outcome = decide(FIRST_ROUND, first_round(700, 200, 50, remaining=400))

    assert outcome.verdict is Verdict.ELECTED


def test_stays_undecided_while_majority_can_be_lost() -> None:
    outcome = decide(FIRST_ROUND, first_round(600, 300, 100, remaining=300))

    assert outcome.verdict is Verdict.UNDECIDED
    assert outcome.finalists == ()


def test_sends_top_two_to_runoff_when_complete() -> None:
    outcome = decide(FIRST_ROUND, first_round(480, 420, 100))

    assert outcome.verdict is Verdict.RUNOFF
    assert outcome.finalists == (NICO, KEONS)


def test_secures_runoff_before_complete() -> None:
    outcome = decide(FIRST_ROUND, first_round(450, 400, 100, remaining=50))

    assert outcome.verdict is Verdict.RUNOFF


def test_waits_while_third_place_can_reach_runoff() -> None:
    outcome = decide(FIRST_ROUND, first_round(450, 400, 380, remaining=50))

    assert outcome.verdict is Verdict.UNDECIDED


def test_oldest_candidate_wins_a_tie_for_runoff() -> None:
    outcome = decide(FIRST_ROUND, first_round(300, 450, 300))

    assert outcome.finalists == (KEONS, NICO)


def test_second_round_elects_leader_when_complete() -> None:
    tally = make_tally({NICO.number: 480, KEONS.number: 520})

    outcome = decide(SECOND_ROUND, tally)

    assert outcome.verdict is Verdict.ELECTED
    assert outcome.finalists == (KEONS,)


def test_second_round_tie_elects_oldest() -> None:
    tally = make_tally({NICO.number: 500, KEONS.number: 500})

    assert decide(SECOND_ROUND, tally).finalists == (NICO,)


def test_second_round_waits_while_lead_can_be_overturned() -> None:
    tally = make_tally({NICO.number: 480, KEONS.number: 520}, remaining=100)

    assert decide(SECOND_ROUND, tally).verdict is Verdict.UNDECIDED


def test_second_round_elects_once_lead_exceeds_remaining() -> None:
    tally = make_tally({NICO.number: 380, KEONS.number: 520}, remaining=100)

    assert decide(SECOND_ROUND, tally).verdict is Verdict.ELECTED
