# test helper functions
import pytest

from titr.helper import is_float


@pytest.mark.parametrize(
    "item, expected",
    [
        ("yankee", False),
        ("dOODlE", False),
        ("KLJF#*(@#!!", False),
        (".34", True),
        (".23191", True),
        ("0", True),
        ("-0", True),
        ("99", True),
        ("4e5", True),
        ("inf", True),
        (5, True),
        (4.1, True),
        (-4.23e-5, True),
        (False, True),
        ("NaN", True),
    ],
)
def test_is_float(item, expected):
    assert is_float(item) is expected
