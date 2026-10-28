"""The same sqlo code, run on every database, must return the same rows."""

import pytest

from sqlo import JSON, Condition, Raw, Window, func, values_of

from .conftest import numbers

pytestmark = pytest.mark.integration

U = {1: (1, "x"), 2: (2, "y"), 3: (3, "z")}  # id -> (a, name) in the seed data


# --- SELECT ---------------------------------------------------------------------


def test_where_order_limit_offset(db):
    q = (
        db.q.select("id", "name")
        .from_("u")
        .where("a >", 0)
        .order_by("-id")
        .limit(2)
        .offset(1)
    )
    assert db.run(q) == [(2, "y"), (1, "x")]


def test_in_and_not_in(db):
    q = (
        db.q.select("id")
        .from_("u")
        .where_in("id", [1, 2])
        .where_not_in("a", [9])
        .order_by("id")
    )
    assert db.run(q) == [(1,), (2,)]


def test_empty_in_and_not_in(db):
    assert db.run(db.q.select("id").from_("u").where_in("id", [])) == []
    q = db.q.select("id").from_("u").where_not_in("id", []).order_by("id")
    assert db.run(q) == [(1,), (2,), (3,)]


def test_in_subquery(db):
    sub = db.q.select("id").from_("v").where("k", 10)
    assert db.run(db.q.select("id").from_("u").where_in("id", sub)) == [(1,)]


def test_like_between_and_null_checks(db):
    assert db.run(db.q.select("id").from_("u").where_like("name", "x%")) == [(1,)]
    q = db.q.select("id").from_("u").where_not_like("name", "x%").order_by("id")
    assert db.run(q) == [(2,), (3,)]
    q = db.q.select("id").from_("u").where_between("a", 1, 2).order_by("id")
    assert db.run(q) == [(1,), (2,)]
    assert db.run(db.q.select("id").from_("u").where_null("d")) == [(3,)]
    q = db.q.select("id").from_("u").where_not_null("d").order_by("id")
    assert db.run(q) == [(1,), (2,)]


def test_condition_tree(db):
    cond = (Condition("a", 1) | Condition("a", 2)) & Condition("name", "x", "!=")
    assert db.run(db.q.select("id").from_("u").where(cond)) == [(2,)]


def test_exists_and_raw_predicates(db):
    sub = db.q.select("id").from_("v").where("k", 10)
    q = db.q.select("id").from_("u").where(Condition.exists(sub)).order_by("id")
    assert db.run(q) == [(1,), (2,), (3,)]
    q = (
        db.q.select("id")
        .from_("u")
        .where(Condition(Raw("a + %s > 2", [1])))
        .order_by("id")
    )
    assert db.run(q) == [(2,), (3,)]


def test_distinct_group_by_and_having(db):
    q = db.q.select("user_id").distinct().from_("o").order_by("user_id")
    assert db.run(q) == [(1,), (2,)]
    q = (
        db.q.select("user_id", func.count("*").as_("n"))
        .from_("o")
        .group_by("user_id")
        .order_by("user_id")
    )
    assert db.run(q) == [(1, 2), (2, 1)]
    q = (
        db.q.select("user_id", func.count("*").as_("n"))
        .from_("o")
        .group_by("user_id")
        .having(Raw("COUNT(*) > %s", [1]))
    )
    assert db.run(q) == [(1, 2)]


# --- JOINs and subqueries --------------------------------------------------------


def test_joins(db):
    q = (
        db.q.select("u.id", "o.total")
        .from_("u")
        .join("o", "o.user_id = u.id")
        .order_by("o.id")
    )
    assert db.run(q) == [(1, 100), (1, 200), (2, 50)]
    q = (
        db.q.select("u.id")
        .from_("u")
        .left_join("o", "o.user_id = u.id")
        .where_null("o.id")
    )
    assert db.run(q) == [(3,)]
    assert db.run(db.q.select(func.count("*")).from_("u").cross_join("v")) == [(6,)]


def test_join_on_a_condition_with_a_bound_value(db):
    on = Condition("o.user_id", Raw("u.id")) & Condition("o.total", 100)
    assert db.run(db.q.select("u.id").from_("u").join("o", on)) == [(1,)]


def test_join_a_subquery_and_select_from_a_derived_table(db):
    sub = db.q.select("id").from_("v").where("k", 10).as_("lo")
    assert db.run(db.q.select("u.id").from_("u").join(sub, "lo.id = u.id")) == [(1,)]
    derived = db.q.select("id").from_("v").as_("s")
    assert db.run(db.q.select("s.id").from_(derived).order_by("s.id")) == [(1,), (2,)]


def test_union_and_union_all_with_a_limit(db):
    both = db.q.select("id").from_("u").union(db.q.select("id").from_("v"))
    assert db.run(both.order_by("id")) == [(1,), (2,), (3,)]
    both = (
        db.q.select("id")
        .from_("u")
        .union(db.q.select("id").from_("v"))
        .order_by("id")
        .limit(2)
    )
    assert db.run(both) == [(1,), (2,)]
    twice = (
        db.q.select("id")
        .from_("v")
        .union_all(db.q.select("id").from_("v"))
        .order_by("id")
    )
    assert db.run(twice) == [(1,), (1,), (2,), (2,)]


def test_a_union_operand_with_its_own_order_and_limit(db):
    operand = db.q.select("id").from_("v").order_by("id").limit(1)
    q = db.q.select("id").from_("u").where("id", 3).union(operand).order_by("id")
    assert db.run(q) == [(1,), (3,)]


def test_ctes(db):
    cte = db.q.select("id").from_("u").where("a", 1)
    assert db.run(db.q.select("*").from_("c").with_(cte, "c")) == [(1,)]
    raw = Raw("SELECT id FROM u WHERE a = %s", [2])
    assert db.run(db.q.select("id").from_("c").with_(raw, "c")) == [(2,)]


# --- window functions ---------------------------------------------------------------


def test_window_functions(db):
    running = func.sum("a").over(
        Window.order_by("id").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
    )
    q = db.q.select("id", running.as_("s")).from_("u").order_by("id")
    assert numbers(db.run(q)) == [(1, 1), (2, 3), (3, 6)]
    previous = func.lag("a", 1).over(Window.order_by("id"))
    q = db.q.select("id", previous.as_("p")).from_("u").order_by("id")
    assert db.run(q) == [(1, None), (2, 1), (3, 2)]
    rank = func.row_number().over(Window.partition_by("user_id").and_order_by("-id"))
    q = db.q.select("id", rank.as_("rn")).from_("o").order_by("id")
    assert db.run(q) == [(1, 2), (2, 1), (3, 1)]


def test_a_window_frame_with_an_interval(db):
    frame = Window.order_by("ts").range_between(
        "INTERVAL 1 DAY PRECEDING", "CURRENT ROW"
    )
    q = db.q.select("id", func.sum("a").over(frame).as_("s")).from_("u").order_by("id")
    assert numbers(db.run(q)) == [(1, 1), (2, 3), (3, 5)]


# --- JSON --------------------------------------------------------------------------


def test_json_paths_return_the_same_text(db):
    def one(path):
        return db.run(db.q.select(JSON("d").extract(path)).from_("u").where("id", 1))

    assert one("a.b") == [("5",)]
    assert one("a.c[1].b") == [("9",)]
    assert one("list[1]") == [("20",)]


def test_a_json_path_in_where(db):
    q = db.q.select("id").from_("u").where(JSON("d").extract("a.b"), "5")
    assert db.run(q) == [(1,)]


# --- INSERT, UPDATE, DELETE ---------------------------------------------------------


def test_insert_variants(db):
    assert db.run(db.q.insert_into("v").values({"id": 9, "k": 90})) == 1
    assert (
        db.run(db.q.insert_into("v").values([{"id": 7, "k": 70}, {"id": 8, "k": 80}]))
        == 2
    )
    q = db.q.insert_into("v").from_select(
        ["id", "k"], db.q.select("id", "a").from_("u").where("id", 3)
    )
    assert db.run(q) == 1
    assert db.run(db.q.select("id", "k").from_("v").order_by("id")) == [
        (1, 10), (2, 20), (3, 3), (7, 70), (8, 80), (9, 90),
    ]  # fmt: skip


def test_update_variants(db):
    assert db.run(db.q.update("u").set({"a": 7}).where("id", 1)) == 1
    assert db.run(db.q.update("u").set({"a": Raw("a + %s", [5])}).where("id", 2)) == 1
    sub = db.q.select("k").from_("v").where("id", 1)
    assert db.run(db.q.update("u").set({"b": sub}).where("id", 3)) == 1
    assert db.run(db.q.select("id", "a", "b").from_("u").order_by("id")) == [
        (1, 7, 1), (2, 7, 2), (3, 3, 10),
    ]  # fmt: skip


def test_batch_update_and_update_all_rows(db):
    q = db.q.update("u").batch_update([{"id": 1, "a": 11}, {"id": 2, "a": 22}], "id")
    assert db.run(q) == 2
    assert db.run(db.q.select("a").from_("u").order_by("id")) == [(11,), (22,), (3,)]
    assert db.run(db.q.update("u").set({"b": 0}).allow_all_rows()) == 3


def test_delete_variants(db):
    assert db.run(db.q.delete_from("u").where("id", 1)) == 1
    sub = db.q.select("id").from_("v").where("k", 20)
    assert db.run(db.q.delete_from("u").where_in("id", sub)) == 1
    assert db.run(db.q.select("id").from_("u")) == [(3,)]
    assert db.run(db.q.delete_from("o").allow_all_rows()) == 3


# --- portable upsert -----------------------------------------------------------------


def _v(db):
    return db.run(db.q.select("id", "k").from_("v").order_by("id"))


def test_on_conflict_do_update_changes_the_row_on_a_conflict(db):
    q = (
        db.q.insert_into("v")
        .values({"id": 1, "k": 999})
        .on_conflict("id")
        .do_update({"k": values_of("k")})
    )
    db.run(q)
    assert _v(db) == [(1, 999), (2, 20)]


def test_on_conflict_do_nothing_leaves_the_row(db):
    db.run(
        db.q.insert_into("v").values({"id": 1, "k": 999}).on_conflict("id").do_nothing()
    )
    assert _v(db) == [(1, 10), (2, 20)]


def test_on_conflict_inserts_when_there_is_no_conflict(db):
    q = (
        db.q.insert_into("v")
        .values({"id": 9, "k": 90})
        .on_conflict("id")
        .do_update({"k": values_of("k")})
    )
    db.run(q)
    assert _v(db) == [(1, 10), (2, 20), (9, 90)]


def test_on_conflict_with_several_rows(db):
    rows = [{"id": 1, "k": 111}, {"id": 3, "k": 333}]
    db.run(
        db.q.insert_into("v")
        .values(rows)
        .on_conflict("id")
        .do_update({"k": values_of("k")})
    )
    assert _v(db) == [(1, 111), (2, 20), (3, 333)]


def test_on_conflict_with_an_expression_and_a_plain_value(db):
    q = (
        db.q.insert_into("v")
        .values({"id": 1, "k": 0})
        .on_conflict("id")
        .do_update({"k": Raw("v.k + %s", [5])})
    )
    db.run(q)
    assert _v(db) == [(1, 15), (2, 20)]
    db.run(
        db.q.insert_into("v")
        .values({"id": 2, "k": 0})
        .on_conflict("id")
        .do_update({"k": 77})
    )
    assert _v(db) == [(1, 15), (2, 77)]


def test_on_conflict_with_insert_select(db):
    source = db.q.select("id", "a").from_("u")
    db.run(
        db.q.insert_into("v")
        .from_select(["id", "k"], source)
        .on_conflict("id")
        .do_nothing()
    )
    assert _v(db) == [(1, 10), (2, 20), (3, 3)]
    db.run(
        db.q.insert_into("v")
        .from_select(["id", "k"], source)
        .on_conflict("id")
        .do_update({"k": values_of("k")})
    )
    assert _v(db) == [(1, 1), (2, 2), (3, 3)]
