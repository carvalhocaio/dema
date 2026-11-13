from dema.monitoring.rate import RateMeter


def test_reports_nothing_before_the_first_sample() -> None:
    meter = RateMeter()

    assert (meter.rate, meter.peak, meter.history) == (0.0, 0.0, ())


def test_measures_the_slope_over_the_window() -> None:
    meter = RateMeter(window_seconds=2.0, sample_seconds=1.0)

    for at, counted in ((0.0, 0), (1.0, 100), (2.0, 300), (3.0, 400)):
        meter.observe(at, counted)

    assert meter.history == (0.0, 100.0, 150.0, 150.0)
    assert meter.rate == 150.0
    assert meter.peak == 150.0


def test_ignores_samples_closer_than_the_spacing() -> None:
    meter = RateMeter(sample_seconds=1.0)

    meter.observe(0.0, 0)
    meter.observe(0.5, 500)
    meter.observe(1.0, 100)

    assert meter.history == (0.0, 100.0)


def test_keeps_the_peak_after_the_count_slows_down() -> None:
    meter = RateMeter(window_seconds=1.0, sample_seconds=1.0, history_size=2)

    for at, counted in ((0.0, 0), (1.0, 900), (2.0, 950), (3.0, 960)):
        meter.observe(at, counted)

    assert meter.history == (50.0, 10.0)
    assert meter.peak == 900.0


def test_never_reports_a_negative_rate() -> None:
    meter = RateMeter(sample_seconds=1.0)

    meter.observe(0.0, 500)
    meter.observe(1.0, 0)

    assert meter.rate == 0.0
