"""MySQL-only behaviour, and the MySQL facts the design relies on."""

import pytest

from sqlo import JSON, Condition, Raw, UnsupportedFeatureError, Window, func, values_of

pymysql = pytest.importorskip("pymysql")
pytestmark = pytest.mark.integration


def _ids(db, table="u"):
    return [row[0] for row in db.run(db.q.select("id").from_(table).order_by("id"))]


# --- multi-table DELETE and UPDATE -------------------------------------------------


def test_delete_with_an_inner_join_removes_the_matching_rows(mysql):
    q = mysql.q.delete_from("u").join("o", "o.user_id = u.id").where("o.total >", 60)
    assert mysql.run(q) == 1  # user 1 has two such orders but is deleted once
    assert _ids(mysql) == [2, 3]


def test_delete_with_a_left_join_finds_rows_without_a_match(mysql):
    q = mysql.q.delete_from("u").left_join("o", "o.user_id = u.id").where_null("o.id")
    assert mysql.run(q) == 1
    assert _ids(mysql) == [1, 2]


def test_delete_with_two_joins_and_a_bound_on_condition(mysql):
    q = (
        mysql.q.delete_from("u")
        .join("o", Raw("o.user_id = u.id AND o.total > %s", [60]))
        .left_join("v", "v.id = u.id")
        .where("u.a", 1)
    )
    assert mysql.run(q) == 1
    on = Condition("o.user_id", Raw("u.id")) & Condition("o.total", 50)
    assert mysql.run(mysql.q.delete_from("u").join("o", on).where("u.a", 2)) == 1
    assert _ids(mysql) == [3]


def test_delete_with_a_join_and_a_cte(mysql):
    q = (
        mysql.q.delete_from("u")
        .with_(Raw("SELECT %s AS n", [1]), "c")
        .join("c", "c.n = u.id")
        .where("u.a", 1)
    )
    assert mysql.run(q) == 1


def test_update_with_a_join(mysql):
    q = mysql.q.update("u").set({"a": 9}).join("v", "u.id = v.id").where("u.id", 1)
    assert mysql.run(q) == 1
    assert mysql.run(mysql.q.select("a").from_("u").where("id", 1)) == [(9,)]


def test_single_table_delete_and_update_keep_order_by_and_limit(mysql):
    assert (
        mysql.run(mysql.q.delete_from("u").where("id >", 0).order_by("-id").limit(1))
        == 1
    )
    assert _ids(mysql) == [1, 2]
    assert (
        mysql.run(
            mysql.q.update("u").set({"b": 5}).where("id >", 0).order_by("id").limit(1)
        )
        == 1
    )


def test_sqlo_rejects_a_join_with_order_by_or_limit_and_so_does_mysql(mysql):
    with pytest.raises(ValueError, match="DELETE.*JOIN"):
        mysql.q.delete_from("u").join("v", "u.id = v.id").where("u.id", 1).limit(
            1
        ).build()
    with pytest.raises(ValueError, match="UPDATE.*JOIN"):
        mysql.q.update("u").set({"a": 1}).join("v", "u.id = v.id").where(
            "u.id", 1
        ).order_by("id").build()
    # the facts behind those errors
    with pytest.raises(pymysql.MySQLError):
        mysql.execute("DELETE u FROM u INNER JOIN v ON u.id = v.id LIMIT 1")
    with pytest.raises(pymysql.MySQLError):
        mysql.execute("UPDATE u INNER JOIN v ON u.id = v.id SET a = 1 ORDER BY u.id")


def test_the_old_delete_join_form_is_a_syntax_error_in_mysql(mysql):
    with pytest.raises(pymysql.MySQLError, match="1064"):
        mysql.execute("DELETE FROM u INNER JOIN v ON u.id = v.id WHERE u.id = 1")


# --- hints, operators, JSON, windows -------------------------------------------------


def test_index_and_optimizer_hints_run(mysql):
    q = (
        mysql.q.select("id")
        .from_("u")
        .force_index("PRIMARY")
        .optimizer_hint("MAX_EXECUTION_TIME(1000)")
        .order_by("id")
    )
    assert mysql.run(q) == [(1,), (2,), (3,)]


def test_mysql_operators(mysql):
    q = mysql.q.select("id").from_("u").where("name REGEXP", "^[xy]").order_by("id")
    assert mysql.run(q) == [(1,), (2,)]
    q = mysql.q.select("id").from_("u").where("a <=>", 2)
    assert mysql.run(q) == [(2,)]


def test_a_json_path_with_a_wildcard_runs(mysql):
    q = mysql.q.select(JSON("d").extract("list[*]")).from_("u").where("id", 1)
    assert mysql.run(q) == [("[10, 20]",)]


def test_window_frame_intervals_run_as_written(mysql):
    for unit in ("DAY", "WEEK", "MONTH", "QUARTER", "YEAR"):
        frame = Window.order_by("ts").range_between(
            f"INTERVAL 1 {unit} PRECEDING", "CURRENT ROW"
        )
        q = mysql.q.select(func.sum("a").over(frame)).from_("u")
        assert len(mysql.run(q)) == 3


# --- upsert ----------------------------------------------------------------------------


def test_the_legacy_upsert_still_works(mysql):
    q = (
        mysql.q.insert_into("v")
        .values({"id": 1, "k": 5})
        .on_duplicate_key_update({"k": values_of("k")})
    )
    mysql.run(q)
    assert mysql.run(mysql.q.select("k").from_("v").where("id", 1)) == [(5,)]


def test_do_nothing_is_a_noop_update_so_it_does_not_hide_truncation(mysql):
    """INSERT IGNORE swallows a too-long value; the no-op update reports it."""
    mysql.run(mysql.q.insert_into("w").values({"id": 1, "s": "ab"}).ignore())
    too_long = mysql.q.insert_into("w").values({"id": 2, "s": "abcdef"})
    assert mysql.run(too_long.ignore()) == 1  # silently truncated
    with pytest.raises(pymysql.MySQLError, match="1406"):
        mysql.run(
            mysql.q.insert_into("w")
            .values({"id": 3, "s": "abcdef"})
            .on_conflict("id")
            .do_nothing()
        )


# --- what sqlo refuses before it reaches MySQL ------------------------------------------


def test_full_join_is_rejected_before_it_reaches_mysql(mysql):
    with pytest.raises(UnsupportedFeatureError, match="FULL"):
        mysql.q.select("*").from_("u").join("v", "u.id = v.id", join_type="FULL OUTER")
    with pytest.raises(pymysql.MySQLError, match="1064"):  # the fact behind it
        mysql.execute("SELECT * FROM u FULL OUTER JOIN v ON u.id = v.id")


def test_a_derived_table_needs_an_alias_in_mysql_and_in_sqlo(mysql):
    with pytest.raises(ValueError, match="alias"):
        mysql.q.select("*").from_(mysql.q.select("id").from_("v")).build()
    with pytest.raises(pymysql.MySQLError, match="1248"):
        mysql.execute("SELECT * FROM (SELECT id FROM v)")


def test_offset_needs_a_limit_in_mysql_and_in_sqlo(mysql):
    with pytest.raises(ValueError, match="offset"):
        mysql.q.select("*").from_("u").offset(1).build()
    with pytest.raises(pymysql.MySQLError, match="1064"):
        mysql.execute("SELECT * FROM u OFFSET 1")


def test_postgresql_operators_are_rejected(mysql):
    with pytest.raises(UnsupportedFeatureError, match="MySQL"):
        mysql.q.select("id").from_("u").where("name ILIKE", "x%")
