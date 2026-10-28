import pytest

from sqlo import Condition, Q, Raw
from sqlo.expressions import ComplexCondition

A, B, C = Condition("a", 1), Condition("b", 2), Condition("c", 3)


# --- mixing Condition and ComplexCondition ----------------------------


def test_condition_and_complex():
    sql, params = (C & (A | B)).build()
    assert sql == "(`c` = %s AND (`a` = %s OR `b` = %s))"
    assert params == (3, 1, 2)


def test_complex_and_condition():
    sql, params = ((A | B) & C).build()
    assert sql == "((`a` = %s OR `b` = %s) AND `c` = %s)"
    assert params == (1, 2, 3)


def test_complex_and_complex_and_or_mixes():
    sql, params = ((A | B) & (C | Condition("d", 4))).build()
    assert sql == "((`a` = %s OR `b` = %s) AND (`c` = %s OR `d` = %s))"
    assert params == (1, 2, 3, 4)
    sql, params = (C | (A & B)).build()
    assert sql == "(`c` = %s OR (`a` = %s AND `b` = %s))"
    assert params == (3, 1, 2)


def test_condition_and_complex_in_a_query():
    sql, params = Q.select("*").from_("u").where(C & (A | B)).build()
    assert sql == ("SELECT * FROM `u` WHERE ((`c` = %s AND (`a` = %s OR `b` = %s)))")
    assert params == (3, 1, 2)


@pytest.mark.parametrize("operand", ["x", 5, None, Raw("1")])
def test_non_condition_operands_are_rejected(operand):
    with pytest.raises(TypeError):
        A & operand
    with pytest.raises(TypeError):
        A | operand
    with pytest.raises(TypeError):
        (A | B) & operand
    with pytest.raises(TypeError):
        (A | B) | operand


# --- empty conditions are the identity of & and | ---------------------


@pytest.mark.parametrize(
    "combined, expected",
    [
        (lambda: Condition() & A, A),
        (lambda: A & Condition(), A),
        (lambda: Condition() | A, A),
        (lambda: A | Condition(), A),
        (lambda: Condition() & (A | B), A | B),
        (lambda: (A | B) & Condition(), A | B),
        (lambda: Condition() | (A | B), A | B),
        (lambda: (A | B) | Condition(), A | B),
        (lambda: (A & B) | Condition(), A & B),
    ],
)
def test_empty_condition_is_the_identity(combined, expected):
    assert combined().build() == expected.build()


@pytest.mark.parametrize(
    "empty",
    [
        lambda: Condition(),
        lambda: Condition() & Condition(),
        lambda: Condition() | Condition(),
        lambda: Condition.and_(),
        lambda: Condition.or_(),
        lambda: (Condition() | Condition()) & Condition(),
    ],
)
def test_all_empty_builds_to_nothing(empty):
    assert empty().build() == ("", ())


def test_or_without_arguments_is_still_a_complex_condition():
    assert isinstance(Condition.or_(), ComplexCondition)


def test_accumulating_filters_starting_from_an_empty_condition():
    filters = [Condition("a", 1), Condition("b", 2), Condition("c", 3)]
    acc = Condition()
    for f in filters:
        acc = acc & f
    assert acc.build() == ("(`a` = %s AND `b` = %s AND `c` = %s)", (1, 2, 3))

    acc = Condition()
    for f in filters:
        acc = acc | f
    assert acc.build() == ("((`a` = %s OR `b` = %s) OR `c` = %s)", (1, 2, 3))


# --- empty conditions never reach SQL ---------------------------------

EMPTIES = [
    lambda: Condition(),
    lambda: Condition.and_(),
    lambda: Condition.or_(),
    lambda: Condition() | Condition(),
]


@pytest.mark.parametrize("empty", EMPTIES)
def test_where_rejects_empty_conditions(empty):
    with pytest.raises(ValueError, match="Empty condition"):
        Q.select("*").from_("u").where(empty())
    with pytest.raises(ValueError, match="Empty condition"):
        Q.select("*").from_("u").where("x", 1).or_where(empty())
    with pytest.raises(ValueError, match="Empty condition"):
        Q.select("*").from_("u").group_by("g").having(empty())
    with pytest.raises(ValueError, match="Empty condition"):
        Q.update("u").set({"a": 1}).where(empty())
    with pytest.raises(ValueError, match="Empty condition"):
        Q.delete_from("u").where(empty())


def test_where_accepts_a_condition_built_from_an_empty_accumulator():
    acc = Condition() & A
    sql, params = Q.select("*").from_("u").where(acc).build()
    assert sql == "SELECT * FROM `u` WHERE (`a` = %s)"
    assert params == (1,)
