"""Conditions render with the dialect of the query (or build argument) they are used in."""

import pytest

from sqlo import Condition, Q, Raw
from sqlo.dialects.base import Dialect
from sqlo.dialects.mysql import MySQLDialect
from sqlo.query.select import SelectQuery


class AnsiDialect(Dialect):
    """Test-only dialect: double-quoted identifiers and `?` placeholders."""

    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


ANSI = AnsiDialect()


def _select(dialect=ANSI):
    return SelectQuery("*", dialect=dialect).from_("u")


# --- standalone build -------------------------------------------------


def test_build_uses_given_dialect():
    sql, params = Condition("a", 1).build(ANSI)
    assert sql == '"a" = ?'
    assert params == (1,)


def test_build_defaults_to_the_global_default_dialect():
    original = Q.get_dialect()
    try:
        Q.set_dialect(ANSI)
        assert Condition("a", 1).build() == ('"a" = ?', (1,))
    finally:
        Q.set_dialect(original)
    assert Condition("a", 1).build() == ("`a` = %s", (1,))


def test_complex_condition_build_uses_given_dialect():
    c = (Condition("a", 1) & Condition("b", 2)) | Condition("c", 3)
    sql, params = c.build(ANSI)
    assert sql == '(("a" = ? AND "b" = ?) OR "c" = ?)'
    assert params == (1, 2, 3)


def test_same_condition_renders_in_two_dialects():
    c = Condition("u.age>", 18) & Condition("name", "x", "LIKE")
    assert c.build(MySQLDialect()) == (
        "(`u`.`age` > %s AND `name` LIKE %s)",
        (18, "x"),
    )
    assert c.build(ANSI) == ('("u"."age" > ? AND "name" LIKE ?)', (18, "x"))


# --- inside queries ---------------------------------------------------


def test_where_renders_condition_with_query_dialect():
    sql, params = _select().where(Condition("a", 1) & Condition("b", 2)).build()
    assert sql == 'SELECT * FROM "u" WHERE (("a" = ? AND "b" = ?))'
    assert params == (1, 2)


def test_or_where_and_having_render_with_query_dialect():
    sql, params = (
        _select()
        .where("x", 0)
        .or_where(Condition("a", 1) | Condition("b", 2))
        .group_by("g")
        .having(Condition("n>", 5))
        .build()
    )
    assert sql == (
        'SELECT * FROM "u" WHERE "x" = ? OR (("a" = ? OR "b" = ?)) '
        'GROUP BY "g" HAVING ("n" > ?)'
    )
    assert params == (0, 1, 2, 5)


@pytest.mark.parametrize(
    "cond, expected_sql, expected_params",
    [
        (Condition.null("a"), '("a" IS NULL)', ()),
        (Condition.not_null("a"), '("a" IS NOT NULL)', ()),
        (Condition.in_("a", [1, 2]), '("a" IN (?, ?))', (1, 2)),
        (Condition("a", Raw("b.c")), '("a" = b.c)', ()),
        (Condition("a", Raw("? + 1", [5])), '("a" = ? + 1)', (5,)),
    ],
)
def test_condition_kinds_render_with_query_dialect(cond, expected_sql, expected_params):
    sql, params = _select().where(cond).build()
    assert sql == f"SELECT * FROM \"u\" WHERE {expected_sql}"
    assert params == expected_params


def test_in_subquery_and_exists_render_with_query_dialect():
    sub = SelectQuery("id", dialect=ANSI).from_("v").where("k", 9)
    sql, params = _select().where(Condition.in_("a", sub)).build()
    assert sql == 'SELECT * FROM "u" WHERE ("a" IN (SELECT "id" FROM "v" WHERE "k" = ?))'
    assert params == (9,)

    sql, params = _select().where(Condition.exists(sub)).build()
    assert sql == 'SELECT * FROM "u" WHERE (EXISTS (SELECT "id" FROM "v" WHERE "k" = ?))'
    assert params == (9,)


def test_params_keep_sql_order_with_nested_subquery():
    sub = SelectQuery("id", dialect=ANSI).from_("v").where("k", "sub")
    cond = Condition("a", "first") & Condition.in_("b", sub) & Condition("c", "last")
    _, params = _select().where(cond).build()
    assert params == ("first", "sub", "last")


def test_subquery_with_a_different_dialect_is_rejected():
    sub = SelectQuery("id", dialect=MySQLDialect()).from_("v")
    with pytest.raises(ValueError, match="dialect"):
        _select().where(Condition.in_("a", sub)).build()
    with pytest.raises(ValueError, match="dialect"):
        _select().where(Condition.exists(sub)).build()


# --- validation happens at construction -------------------------------


@pytest.mark.parametrize(
    "column",
    ['a"; DROP TABLE x;--', "a`; DROP TABLE x;--", "a b", "", "1a", "a;b"],
)
def test_invalid_column_rejected_at_construction(column):
    with pytest.raises(ValueError):
        Condition(column, 1)
    with pytest.raises(ValueError):
        Condition(column, operator="IS NULL")
    with pytest.raises(ValueError):
        Condition.in_(column, [1])
    with pytest.raises(ValueError):
        Condition.null(column)
