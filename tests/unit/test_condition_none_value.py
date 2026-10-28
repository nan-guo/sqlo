import pytest

from sqlo import Condition, Q


@pytest.mark.parametrize("operator", ["=", "!=", "<>", "<", ">=", "LIKE", "NOT LIKE"])
def test_none_value_needs_an_is_operator(operator):
    with pytest.raises(ValueError, match="IS NULL"):
        Condition("a", None, operator)


def test_missing_value_is_rejected():
    with pytest.raises(ValueError, match="IS NULL"):
        Condition("a")


@pytest.mark.parametrize("column", ["age>", "age >=", "name LIKE"])
def test_none_value_rejected_with_embedded_operator(column):
    with pytest.raises(ValueError, match="IS NULL"):
        Condition(column, None)


def test_error_message_names_the_column():
    with pytest.raises(ValueError, match="'deleted_at'"):
        Condition("deleted_at", None)


def test_none_value_never_reaches_a_query_as_an_empty_condition():
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where(Condition("a", None))


@pytest.mark.parametrize(
    "build, expected",
    [
        (lambda: Condition("a", None, "IS"), "`a` IS NULL"),
        (lambda: Condition("a", None, "IS NOT"), "`a` IS NOT NULL"),
        (lambda: Condition("a", operator="IS NULL"), "`a` IS NULL"),
        (lambda: Condition("a", operator="IS NOT NULL"), "`a` IS NOT NULL"),
        (lambda: Condition.null("a"), "`a` IS NULL"),
        (lambda: Condition.not_null("a"), "`a` IS NOT NULL"),
        (lambda: Condition("a IS", None), "`a` IS NULL"),
    ],
)
def test_is_operators_accept_none(build, expected):
    assert build().build() == (expected, ())


def test_falsy_values_are_not_none():
    for value in (0, False, ""):
        assert Condition("a", value).build() == ("`a` = %s", (value,))


def test_empty_condition_without_a_column_is_still_allowed():
    assert Condition().build() == ("", ())
    assert Condition.and_().build() == ("", ())
