import pytest

from sqlo import Condition, Q, Raw
from sqlo.dialects.base import Dialect


class AnsiDialect(Dialect):
    """Test-only dialect: double-quoted identifiers and `?` placeholders."""

    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


MATCH = Raw("MATCH(title, body) AGAINST(%s)", ["term"])


# --- a Raw predicate on its own ---------------------------------------


def test_raw_predicate_with_params():
    assert Condition(MATCH).build() == ("MATCH(title, body) AGAINST(%s)", ("term",))


def test_raw_predicate_without_params():
    assert Condition(Raw("a > b")).build() == ("a > b", ())


def test_raw_predicate_combines_and_keeps_param_order():
    cond = Condition("x", 1) & Condition(MATCH) & Condition("y", 2)
    assert cond.build() == (
        "(`x` = %s AND MATCH(title, body) AGAINST(%s) AND `y` = %s)",
        (1, "term", 2),
    )
    cond = (Condition("x", 1) | Condition(MATCH)) & Condition("y", 2)
    assert cond.build() == (
        "((`x` = %s OR MATCH(title, body) AGAINST(%s)) AND `y` = %s)",
        (1, "term", 2),
    )


def test_raw_predicate_in_a_query():
    sql, params = Q.select("*").from_("posts").where(Condition(MATCH)).build()
    assert sql == "SELECT * FROM `posts` WHERE (MATCH(title, body) AGAINST(%s))"
    assert params == ("term",)


# --- a Raw expression as the left-hand side ---------------------------


def test_raw_column_with_value_and_operator():
    assert Condition(Raw("LENGTH(password)"), 8, ">").build() == (
        "LENGTH(password) > %s",
        (8,),
    )


def test_raw_column_default_operator_is_equals():
    assert Condition(Raw("LOWER(name)"), "bob").build() == (
        "LOWER(name) = %s",
        ("bob",),
    )


def test_raw_column_params_come_before_the_value_params():
    cond = Condition(Raw("JSON_EXTRACT(d, %s)", ["$.a"]), "x")
    assert cond.build() == ("JSON_EXTRACT(d, %s) = %s", ("$.a", "x"))


def test_raw_column_with_raw_value():
    cond = Condition(Raw("LOWER(a)"), Raw("LOWER(%s)", ["B"]), "=")
    assert cond.build() == ("LOWER(a) = LOWER(%s)", ("B",))


def test_raw_column_with_in_list_and_null_checks():
    assert Condition.in_(Raw("LOWER(a)"), ["x", "y"]).build() == (
        "LOWER(a) IN (%s, %s)",
        ("x", "y"),
    )
    assert Condition.not_in(Raw("LOWER(a)"), []).build() == ("TRUE", ())
    assert Condition.null(Raw("LOWER(a)")).build() == ("LOWER(a) IS NULL", ())
    assert Condition.not_null(Raw("LOWER(a)")).build() == ("LOWER(a) IS NOT NULL", ())
    assert Condition(Raw("LOWER(a)"), None, "IS NOT").build() == (
        "LOWER(a) IS NOT NULL",
        (),
    )


def test_raw_column_in_a_query_with_other_conditions():
    sql, params = (
        Q.select("*")
        .from_("u")
        .where("a", 0)
        .where(Condition(Raw("LENGTH(password)"), 8, ">") & Condition("b", 1))
        .build()
    )
    assert sql == (
        "SELECT * FROM `u` WHERE `a` = %s AND ((LENGTH(password) > %s AND `b` = %s))"
    )
    assert params == (0, 8, 1)


def test_raw_column_uses_the_dialect_for_placeholders():
    ansi = AnsiDialect()
    assert Condition(Raw("LENGTH(p)"), 8, ">").build(ansi) == ("LENGTH(p) > ?", (8,))
    assert Condition(Raw("LOWER(a)"), "x").build(ansi) == ("LOWER(a) = ?", ("x",))


# --- validation still applies -----------------------------------------


def test_raw_column_operator_is_validated():
    with pytest.raises(ValueError):
        Condition(Raw("LENGTH(p)"), 8, "> 1 OR 1=1 --")


def test_raw_column_without_a_value_needs_an_is_operator():
    with pytest.raises(ValueError, match="IS NULL"):
        Condition(Raw("LENGTH(p)"), None, ">")


@pytest.mark.parametrize("column", [123, 1.5, ["a"], object()])
def test_other_column_types_are_rejected(column):
    with pytest.raises(ValueError):
        Condition(column, 1)
