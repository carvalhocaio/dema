import pytest

from tests.factories import make_candidate


@pytest.mark.parametrize("number", [9, 100, 0])
def test_rejects_non_two_digit_numbers(number: int) -> None:
    with pytest.raises(ValueError, match="two digits"):
        make_candidate(number=number)


def test_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="blank"):
        make_candidate(name="")
