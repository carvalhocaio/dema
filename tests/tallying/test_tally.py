import pytest

from dema.tallying.tally import Tally


def make_tally(**overrides: int) -> Tally:
    values = {
        "blank_votes": 10,
        "null_votes": 20,
        "counted_sections": 2,
        "counted_electorate": 1_000,
        "total_sections": 8,
        "total_electorate": 4_000,
    } | overrides
    return Tally(nominal_votes={99: 450, 27: 300}, **values)


def test_derives_vote_totals() -> None:
    tally = make_tally()

    assert tally.valid_votes == 750
    assert tally.turnout == 780
    assert tally.abstentions == 220
    assert tally.remaining_electorate == 3_000


def test_reports_progress() -> None:
    assert make_tally().progress == 0.25
    assert not make_tally().is_complete
    assert make_tally(counted_sections=8, counted_electorate=4_000).is_complete


def test_share_is_based_on_valid_votes() -> None:
    assert make_tally().share(99) == 0.6


def test_share_is_zero_without_valid_votes() -> None:
    tally = Tally(
        nominal_votes={99: 0},
        blank_votes=0,
        null_votes=0,
        counted_sections=0,
        counted_electorate=0,
        total_sections=1,
        total_electorate=300,
    )

    assert tally.share(99) == 0.0
    assert tally.progress == 0.0


@pytest.mark.parametrize(
    "overrides",
    [{"counted_sections": 9}, {"counted_electorate": 5_000}, {"counted_sections": -1}],
)
def test_rejects_counts_beyond_totals(overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="within the total"):
        make_tally(**overrides)
