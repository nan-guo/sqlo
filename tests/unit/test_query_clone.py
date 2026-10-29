import pytest

from sqlo import Condition, Q, Raw
from sqlo.dialects.base import Dialect
from sqlo.query.delete import DeleteQuery
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery
from sqlo.query.update import UpdateQuery


class AnsiDialect(Dialect):
    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


def _full_select():
    sub = Q.select("id").from_("v").where("k", 9).as_("sv")
    return (
        Q.select("a", "b")
        .distinct()
        .from_("t", "x")
        .left_join("o o1", "x.id = o1.tid")
        .where("a", 1)
        .where_in("b", [1, 2, 3])
        .group_by("a")
        .having("n >", 2)
        .order_by("-a")
        .limit(10)
        .offset(5)
        .force_index("idx_a")
        .optimizer_hint("MAX_EXECUTION_TIME(100)")
        .union_all(Q.select("a", "b").from_("w"))
        .with_(sub, "sv")
    )


# --- reusing a base query ------------------------------------------------


def test_cloning_a_base_query_keeps_derived_queries_independent():
    base = Q.select("*").from_("users").where("active", True)
    adults = base.clone().where("age >", 18)
    french = base.clone().where("country", "FR")

    assert base.build() == ("SELECT * FROM `users` WHERE `active` = %s", (True,))
    assert adults.build() == (
        "SELECT * FROM `users` WHERE `active` = %s AND `age` > %s",
        (True, 18),
    )
    assert french.build() == (
        "SELECT * FROM `users` WHERE `active` = %s AND `country` = %s",
        (True, "FR"),
    )


def test_clone_is_a_new_object_of_the_same_type():
    for q in (
        Q.select("a").from_("t"),
        Q.update("t").set({"a": 1}),
        Q.delete_from("t"),
        Q.insert_into("t").values({"a": 1}),
    ):
        c = q.clone()
        assert c is not q
        assert type(c) is type(q)


@pytest.mark.parametrize(
    "make",
    [
        _full_select,
        lambda: Q.update("t").set({"a": 1}).where("id", 1).order_by("id").limit(3),
        lambda: Q.delete_from("t").where("id", 1).order_by("id").limit(3),
        lambda: Q.insert_into("t").values([{"a": 1}, {"a": 2}]).ignore(),
        lambda: Q.update("t").batch_update(
            [{"id": 1, "a": 2}, {"id": 2, "a": 3}], "id"
        ),
        lambda: Q.select("*").from_("t").where(Condition("a", 1) | Condition("b", 2)),
    ],
)
def test_clone_builds_the_same_sql_and_params(make):
    q = make()
    assert q.clone().build() == q.build()


# --- changes to the clone never reach the original ----------------------

MUTATIONS = [
    lambda q: q.where("zz", 1),
    lambda q: q.or_where("zz", 1),
    lambda q: q.where_in("zz", [1]),
    lambda q: q.join("zz", "a = b"),
    lambda q: q.order_by("zz"),
    lambda q: q.group_by("zz"),
    lambda q: q.having("zz", 1),
    lambda q: q.limit(99),
    lambda q: q.offset(99),
    lambda q: q.union(Q.select("a", "b").from_("zz")),
    lambda q: q.optimizer_hint("NO_RANGE_OPTIMIZATION(t)"),
    lambda q: q.force_index("zz"),
    lambda q: q.with_(Q.select("1").from_("zz"), "zz"),
    lambda q: q.explain(),
]


@pytest.mark.parametrize("mutate", MUTATIONS)
def test_mutating_the_clone_leaves_the_original_unchanged(mutate):
    original = _full_select()
    before = original.build()
    clone = original.clone()
    mutate(clone)
    assert original.build() == before
    assert clone.build() != before


def test_update_clone_is_independent():
    original = Q.update("t").set({"a": 1}).where("id", 1)
    clone = original.clone().set({"b": 2}).where("x", 3).limit(1)
    assert original.build() == ("UPDATE `t` SET `a` = %s WHERE `id` = %s", (1, 1))
    assert clone.build()[0].startswith("UPDATE `t` SET `a` = %s, `b` = %s WHERE")


def test_update_clone_with_a_subquery_value_is_independent():
    sub = Q.select("max_v").from_("s").where("k", 1)
    original = Q.update("t").set({"a": sub}).where("id", 1)
    clone = original.clone()
    sub.where("later", 2)  # changes the object the original holds
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


def test_delete_clone_is_independent():
    original = Q.delete_from("t").where("id", 1)
    clone = original.clone().where("x", 2).limit(5)
    assert original.build() == ("DELETE FROM `t` WHERE `id` = %s", (1,))
    assert clone.build()[0] == "DELETE FROM `t` WHERE `id` = %s AND `x` = %s LIMIT 5"


def test_insert_clone_is_independent():
    original = Q.insert_into("t").values({"a": 1})
    clone = (
        original.clone().values({"a": 2}).on_duplicate_key_update({"a": Raw("a + 1")})
    )
    assert original.build() == ("INSERT INTO `t` (`a`) VALUES (%s)", (1,))
    assert clone.build()[0] == (
        "INSERT INTO `t` (`a`) VALUES (%s), (%s) ON DUPLICATE KEY UPDATE `a` = a + 1"
    )


def test_insert_from_select_clone_is_independent():
    sub = Q.select("a").from_("src")
    original = Q.insert_into("t").from_select(["a"], sub)
    clone = original.clone()
    sub.where("later", 1)
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


# --- nested queries are cloned too ---------------------------------------


def test_a_subquery_in_from_is_not_shared():
    sub = Q.select("id").from_("v")
    original = Q.select("*").from_(sub, alias="s")
    clone = original.clone()
    sub.where("later", 1)
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


def test_union_operands_are_not_shared():
    operand = Q.select("a").from_("w")
    original = Q.select("a").from_("t").union(operand)
    clone = original.clone()
    operand.where("later", 1)
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


def test_cte_queries_are_not_shared():
    cte = Q.select("a").from_("w")
    original = Q.select("*").from_("c").with_(cte, "c")
    clone = original.clone()
    cte.where("later", 1)
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


def test_join_subquery_is_not_shared():
    sub = Q.select("uid").from_("o").as_("lo")
    original = Q.select("*").from_("u").join(sub, "lo.uid = u.id")
    clone = original.clone()
    sub.where("later", 1)
    assert "later" in original.build()[0]
    assert "later" not in clone.build()[0]


# --- settings carry over --------------------------------------------------


def test_clone_keeps_the_dialect_and_debug_flag():
    ansi = AnsiDialect()
    original = SelectQuery("a", dialect=ansi, debug=False).from_("t").where("a", 1)
    clone = original.clone()
    assert clone.build() == ('SELECT "a" FROM "t" WHERE "a" = ?', (1,))
    assert clone._dialect is ansi
    assert clone._debug is original._debug


def test_clone_chains_keep_the_concrete_type():
    assert isinstance(Q.select("a").from_("t").clone().where("a", 1), SelectQuery)
    assert isinstance(Q.update("t").set({"a": 1}).clone().where("a", 1), UpdateQuery)
    assert isinstance(Q.delete_from("t").clone().where("a", 1), DeleteQuery)
    assert isinstance(Q.insert_into("t").values({"a": 1}).clone().ignore(), InsertQuery)


def test_cloning_does_not_change_the_original():
    q = _full_select()
    before = q.build()
    q.clone()
    assert q.build() == before
