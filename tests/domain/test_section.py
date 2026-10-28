import pytest

from dema.domain.section import Section, SectionKey
from dema.domain.state import Region, State
from tests.factories import make_section_key


def test_section_key_round_trips_through_string() -> None:
    key = make_section_key(number=42)

    assert str(key) == "MT-90670-0001-0042"
    assert SectionKey.parse(str(key)) == key


def test_section_requires_eligible_voters() -> None:
    with pytest.raises(ValueError, match="eligible voters"):
        Section(key=make_section_key(), eligible_voters=0)


@pytest.mark.parametrize(
    ("state", "region"),
    [
        (State.MT, Region.CENTER_WEST),
        (State.BA, Region.NORTHEAST),
        (State.SP, Region.SOUTHEAST),
        (State.ZZ, Region.ABROAD),
    ],
)
def test_state_maps_to_region(state: State, region: Region) -> None:
    assert state.region is region


def test_every_state_has_a_region() -> None:
    assert all(state.region for state in State)
