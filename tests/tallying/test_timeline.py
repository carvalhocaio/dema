from datetime import UTC, datetime, timedelta

from dema.tallying.outcome import Verdict
from dema.tallying.timeline import MinuteCount, build_timeline
from tests.factories import KEONS, LISDEN, NICO, make_election

ELECTION = make_election()
START = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def minute(offset: int, nico: int, keons: int, lisden: int) -> MinuteCount:
    return MinuteCount(
        minute=START + timedelta(minutes=offset),
        sections=1,
        electorate=nico + keons + lisden + 10,
        blank_votes=2,
        null_votes=3,
        nominal_votes={NICO.number: nico, KEONS.number: keons, LISDEN.number: lisden},
    )


def test_accumulates_minutes_in_chronological_order() -> None:
    late, early = minute(5, 10, 20, 30), minute(1, 1, 2, 3)

    timeline = build_timeline(ELECTION, [late, early], 4, 1_000)

    first, second = timeline.points
    assert (first.at, second.at) == (early.minute, late.minute)
    assert first.tally.nominal_votes == {
        NICO.number: 1,
        KEONS.number: 2,
        LISDEN.number: 3,
    }
    assert second.tally.nominal_votes == {
        NICO.number: 11,
        KEONS.number: 22,
        LISDEN.number: 33,
    }
    assert (second.tally.blank_votes, second.tally.null_votes) == (4, 6)
    assert second.tally.counted_sections == 2
    assert second.tally.progress == 0.5


def test_marks_the_first_minute_with_a_secured_verdict() -> None:
    minutes = [minute(0, 10, 10, 10), minute(1, 400, 100, 50), minute(2, 5, 5, 5)]

    timeline = build_timeline(ELECTION, minutes, 3, 700)

    verdicts = [point.outcome.verdict for point in timeline.points]
    assert verdicts[0] is Verdict.UNDECIDED
    assert verdicts[1] is not Verdict.UNDECIDED
    assert timeline.decided_at == minutes[1].minute


def test_an_undecided_count_has_no_decision_time() -> None:
    timeline = build_timeline(ELECTION, [minute(0, 10, 10, 10)], 10, 10_000)

    assert timeline.decided_at is None


def test_marks_the_minutes_where_the_leader_changed() -> None:
    minutes = [
        minute(0, 10, 50, 5),
        minute(1, 60, 5, 5),
        minute(2, 5, 5, 5),
        minute(3, 5, 200, 5),
    ]

    timeline = build_timeline(ELECTION, minutes, 4, 10_000)

    assert timeline.lead_changes == (minutes[1].minute, minutes[3].minute)


def test_a_steady_lead_has_no_changes() -> None:
    timeline = build_timeline(ELECTION, [minute(0, 10, 50, 5)], 10, 10_000)

    assert timeline.lead_changes == ()
