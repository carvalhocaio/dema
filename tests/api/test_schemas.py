from dema.api.schemas import ResultsView
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.tallying.outcome import Verdict, decide
from tests.api.fakes import make_tally

ELECTION = DEMA_2026_FIRST_ROUND.election


def build(counted_sections: int) -> ResultsView:
    tally = make_tally(counted_sections)
    return ResultsView.build(ELECTION, tally, decide(ELECTION, tally))


def test_lists_candidates_in_ranking_order() -> None:
    view = build(counted_sections=4)

    assert [c.number for c in view.candidates][:2] == [KEONS.number, NICO.number]
    assert view.candidates[0].share == 0.6
    assert view.candidates[0].party == "Torchbearers"


def test_summarizes_progress_and_votes() -> None:
    view = build(counted_sections=4)

    assert view.progress.ratio == 0.4
    assert not view.progress.is_complete
    assert (view.votes.valid, view.votes.turnout) == (1_000, 1_050)
    assert view.votes.abstentions == 150


def test_exposes_verdict_and_finalists() -> None:
    view = build(counted_sections=10)

    assert view.verdict is Verdict.ELECTED
    assert view.finalists == (KEONS.number,)


def test_views_with_same_data_are_equal() -> None:
    assert build(counted_sections=4) == build(counted_sections=4)
    assert build(counted_sections=4) != build(counted_sections=5)
