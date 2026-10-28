import pytest

from sqlo import Condition, Q, Raw
from sqlo.dialects.base import Dialect
from sqlo.query.select import SelectQuery


class AnsiDialect(Dialect):
    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


def _select():
    return Q.select("*").from_("u")


# --- string ON: only `column <op> column [AND ...]` ---------------------


@pytest.mark.parametrize(
    "on",
    [
        "u.id = o.user_id",
        "u.id=o.user_id",
        "a.x <> b.y",
        "a.x != b.y",
        "a.x <=> b.y",
        "a.x >= b.y AND a.z < b.w",
        "a.x = b.y and a.z = b.w",
        "a.x = b.y AND a.z = b.w AND a.k <= b.k",
        "id = user_id",
        "  u.id = o.user_id  ",
    ],
)
def test_simple_column_comparisons_are_accepted_unchanged(on):
    sql, params = _select().join("o", on).build()
    assert sql == f"SELECT * FROM `u` INNER JOIN o ON {on.strip()}"
    assert params == ()


@pytest.mark.parametrize(
    "on",
    [
        "1=1",
        "1=1 OR 1=1",
        "a.x = b.y OR a.z = b.w",
        "a.x = 'active'",
        "a.x = 1",
        "a.x = b.y; DROP TABLE x",
        "a.x = b.y --",
        "a.x = b.y /* c */",
        "DATE(a.x) = b.y",
        "a.x = b.y AND",
        "AND a.x = b.y",
        "a.x = b.y AND 1=1",
        "a.x =",
        "= b.y",
        "a.x == b.y",
        "a.x LIKE b.y",
        "a..x = b.y",
        "(a.x = b.y)",
        "`a`.`x` = b.y",
        "",
        "   ",
    ],
)
def test_anything_else_is_rejected_for_every_query_type(on):
    with pytest.raises(ValueError, match="Raw"):
        _select().join("o", on)
    with pytest.raises(ValueError, match="Raw"):
        Q.update("u").join("o", on)
    with pytest.raises(ValueError, match="Raw"):
        Q.delete_from("u").join("o", on)


@pytest.mark.parametrize(
    "on", [123, 1.5, ["a.x = b.y"], ("a.x", "b.y"), object(), b"a=b"]
)
def test_other_types_are_rejected(on):
    with pytest.raises(TypeError, match="on"):
        _select().join("o", on)
    with pytest.raises(TypeError, match="on"):
        Q.update("u").join("o", on)
    with pytest.raises(TypeError, match="on"):
        Q.delete_from("u").join("o", on)


def test_a_query_is_not_a_valid_on():
    with pytest.raises(TypeError):
        _select().join("o", Q.select("1").from_("x"))


def test_a_rejected_join_leaves_the_query_unchanged():
    q = _select()
    with pytest.raises(ValueError):
        q.join("o", "1=1")
    with pytest.raises(TypeError):
        q.join("o", 5)
    assert q.build()[0] == "SELECT * FROM `u`"


def test_no_on_is_still_allowed():
    sql, _ = _select().cross_join("o").build()
    assert sql == "SELECT * FROM `u` CROSS JOIN o"
    sql, _ = _select().join("o").build()
    assert sql == "SELECT * FROM `u` INNER JOIN o"


# --- Raw and Condition ON -----------------------------------------------


def test_raw_on_without_params():
    sql, params = _select().join("d", Raw("DATE(s.created_at) = d.date")).build()
    assert sql == "SELECT * FROM `u` INNER JOIN d ON DATE(s.created_at) = d.date"
    assert params == ()


def test_raw_on_with_params_come_before_where_params():
    sql, params = (
        _select()
        .join("s", Raw("s.status = %s AND s.uid = u.id", ["active"]))
        .where("u.age >", 18)
        .build()
    )
    assert sql == (
        "SELECT * FROM `u` INNER JOIN s ON s.status = %s AND s.uid = u.id "
        "WHERE `u`.`age` > %s"
    )
    assert params == ("active", 18)


def test_condition_on_validates_columns_and_binds_values():
    on = Condition("s.user_id", Raw("u.id")) & Condition("s.status", "active")
    sql, params = _select().left_join("s", on).build()
    assert sql == (
        "SELECT * FROM `u` LEFT JOIN s ON (`s`.`user_id` = u.id AND `s`.`status` = %s)"
    )
    assert params == ("active",)


def test_complex_condition_on():
    on = Condition("a.x", Raw("b.x")) | Condition("a.y", Raw("b.y"))
    sql, _ = _select().join("b", on).build()
    assert sql.endswith("INNER JOIN b ON (`a`.`x` = b.x OR `a`.`y` = b.y)")


def test_condition_on_rejects_bad_columns_at_construction():
    with pytest.raises(ValueError, match="Invalid identifier"):
        Condition("s.user_id;DROP", Raw("u.id"))


def test_empty_condition_on_is_rejected():
    with pytest.raises(ValueError, match="Empty condition"):
        _select().join("o", Condition())


def test_join_params_follow_sql_order_with_a_subquery_join():
    sub = Q.select("uid").from_("o").where("k", "sub").as_("lo")
    sql, params = (
        _select()
        .join(sub, Raw("lo.uid = u.id AND lo.flag = %s", ["on"]))
        .where("z", "where")
        .build()
    )
    assert params == ("sub", "on", "where")


def test_condition_on_uses_the_dialect_of_the_query():
    on = Condition("s.user_id", Raw("u.id")) & Condition("s.status", "active")
    q = SelectQuery("*", dialect=AnsiDialect()).from_("u").left_join("s", on)
    sql, params = q.build()
    assert (
        sql
        == 'SELECT * FROM "u" LEFT JOIN s ON ("s"."user_id" = u.id AND "s"."status" = ?)'
    )
    assert params == ("active",)


# --- UPDATE and DELETE joins carry their parameters ---------------------


def test_update_join_params_come_before_set_and_where_params():
    sql, params = (
        Q.update("u")
        .set({"a": 1})
        .join("v", Raw("v.k = %s", ["k"]))
        .where("id", 5)
        .build()
    )
    assert sql == ("UPDATE `u` INNER JOIN v ON v.k = %s SET `a` = %s WHERE `id` = %s")
    assert params == ("k", 1, 5)


def test_update_join_with_a_condition():
    on = Condition("v.uid", Raw("u.id")) & Condition("v.flag", True)
    sql, params = Q.update("u").set({"a": 1}).left_join("v", on).where("id", 5).build()
    assert sql == (
        "UPDATE `u` LEFT JOIN v ON (`v`.`uid` = u.id AND `v`.`flag` = %s) "
        "SET `a` = %s WHERE `id` = %s"
    )
    assert params == (True, 1, 5)


def test_delete_join_params_come_before_where_params():
    sql, params = (
        Q.delete_from("u").join("v", Raw("v.k = %s", ["k"])).where("u.id", 5).build()
    )
    assert sql == ("DELETE `u` FROM `u` INNER JOIN v ON v.k = %s WHERE `u`.`id` = %s")
    assert params == ("k", 5)


# --- the helpers share one implementation -------------------------------


@pytest.mark.parametrize("name", ["inner_join", "left_join", "right_join"])
def test_join_helpers_accept_the_same_on_values(name):
    q = getattr(_select(), name)("o", Raw("o.k = %s", [1]))
    assert q.build()[1] == (1,)
    with pytest.raises(ValueError):
        getattr(_select(), name)("o", "1=1")


def test_clone_keeps_join_params_independent():
    original = _select().join("o", Raw("o.k = %s", [1]))
    clone = original.clone().join("p", Raw("p.k = %s", [2]))
    assert original.build()[1] == (1,)
    assert clone.build()[1] == (1, 2)
