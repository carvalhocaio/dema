from datetime import UTC, date, datetime, timedelta

from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionRound
from dema.domain.state import Region
from dema.simulation.scenario import RegionalProfile, Scenario

KEONS = Candidate(
    number=27, name="Keons", party="Torchbearers", birth_date=date(1968, 10, 5)
)
NICO = Candidate(
    number=99, name="Nico", party="Dema Order", birth_date=date(1961, 5, 24)
)
LISDEN = Candidate(
    number=31, name="Lisden", party="Paladin Union", birth_date=date(1975, 5, 17)
)
ANDRE = Candidate(
    number=44, name="Andre", party="Glorious Gone", birth_date=date(1972, 1, 8)
)
VETOMO = Candidate(
    number=12, name="Vetomo", party="Vulture Front", birth_date=date(1979, 5, 21)
)

FIRST_ROUND_POLLS_CLOSE = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def _profile(
    keons: float, nico: float, turnout: float, delay_minutes: int
) -> RegionalProfile:
    return RegionalProfile(
        preferences={
            KEONS.number: keons,
            NICO.number: nico,
            LISDEN.number: 0.045,
            ANDRE.number: 0.03,
            VETOMO.number: 0.015,
        },
        turnout=turnout,
        release_delay=timedelta(minutes=delay_minutes),
    )


DEMA_2026_FIRST_ROUND = Scenario(
    election=Election(
        year=2026,
        round=ElectionRound.FIRST,
        candidates=(KEONS, NICO, LISDEN, ANDRE, VETOMO),
    ),
    profiles={
        Region.SOUTH: _profile(0.36, 0.55, turnout=0.82, delay_minutes=35),
        Region.CENTER_WEST: _profile(0.35, 0.56, turnout=0.78, delay_minutes=45),
        Region.SOUTHEAST: _profile(0.42, 0.48, turnout=0.80, delay_minutes=55),
        Region.NORTH: _profile(0.50, 0.41, turnout=0.77, delay_minutes=70),
        Region.NORTHEAST: _profile(0.66, 0.25, turnout=0.79, delay_minutes=85),
        Region.ABROAD: _profile(0.45, 0.45, turnout=0.40, delay_minutes=150),
    },
    polls_close=FIRST_ROUND_POLLS_CLOSE,
)
