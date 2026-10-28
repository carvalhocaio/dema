import pytest

from dema.domain.candidate import Candidate


@pytest.mark.parametrize("number", [9, 100, 0])
def test_rejects_non_two_digit_numbers(number: int) -> None:
    with pytest.raises(ValueError, match="two digits"):
        Candidate(number=number, name="Andre", party="Dema Order")


def test_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="blank"):
        Candidate(number=10, name="  ", party="Dema Order")
