import pytest

from sqlo import Q


@pytest.mark.parametrize("column", ["²", "١٢", "1²"])
def test_non_ascii_digits_are_not_a_numeric_literal(column):
    with pytest.raises(ValueError):
        Q.select(column).from_("t").build()


def test_ascii_digits_are_still_a_numeric_literal():
    assert Q.select("1").from_("t").build()[0] == "SELECT 1 FROM `t`"
