from collections import deque
from dataclasses import dataclass

WINDOW_SECONDS = 5.0
SAMPLE_SECONDS = 0.9
HISTORY_SIZE = 60


@dataclass(frozen=True, slots=True)
class Sample:
    at: float
    counted: int


class RateMeter:
    """Turns successive counted-section totals into ballots per second.

    A sample is taken at most every `sample_seconds`; the rate is the slope
    over the last `window_seconds`, which smooths the publisher's bursts.
    """

    def __init__(
        self,
        window_seconds: float = WINDOW_SECONDS,
        sample_seconds: float = SAMPLE_SECONDS,
        history_size: int = HISTORY_SIZE,
    ) -> None:
        self._window = window_seconds
        self._spacing = sample_seconds
        self._samples: deque[Sample] = deque()
        self._history: deque[float] = deque(maxlen=history_size)
        self._peak = 0.0

    @property
    def rate(self) -> float:
        return self._history[-1] if self._history else 0.0

    @property
    def peak(self) -> float:
        return self._peak

    @property
    def history(self) -> tuple[float, ...]:
        return tuple(self._history)

    def observe(self, at: float, counted: int) -> None:
        if self._samples and at - self._samples[-1].at < self._spacing:
            return
        self._samples.append(Sample(at, counted))
        while self._samples[0].at < at - self._window:
            self._samples.popleft()
        rate = self._slope()
        self._history.append(rate)
        self._peak = max(self._peak, rate)

    def _slope(self) -> float:
        first, last = self._samples[0], self._samples[-1]
        if last.at == first.at:
            return 0.0
        return max(0.0, (last.counted - first.counted) / (last.at - first.at))
