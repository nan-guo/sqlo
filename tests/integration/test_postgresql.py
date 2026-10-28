"""PostgreSQL-only behaviour, and the PostgreSQL facts the design relies on."""

import pytest

from sqlo import (
    JSON,
    Condition,
    Raw,
    UnsupportedFeatureError,
    Window,
    func,
    values_of,
)

from .conftest import numbers

psycopg = pytest.importorskip("psycopg")
pytestmark = pytest.mark.integration


def _ids(rows):
    return [row[0] for row in rows]


# --- operators --------------------------------------------------------------------------


def test_postgresql_operators(pg):
    def ids(column, value, op):
        return _ids(pg.run(pg.q.select("id").from_("u").where(column, value, op).order_by("id")))

    assert ids("name", "^x", "~") == [1]
    assert ids("name", "^X", "~*") == [1]
    assert ids("name", "^x", "!~") == [2, 3]
    assert ids("name", "^X", "!~*") == [2, 3]
    assert ids("name", "X%", "ILIKE") == [1]
    assert ids("name", "X%", "NOT ILIKE") == [2, 3]
    assert ids("a", 1, "IS DISTINCT FROM") == [2, 3]
    assert ids("a", 1, "IS NOT DISTINCT FROM") == [1]


def test_the_spaced_form_and_conditions_use_the_same_operators(pg):
    assert _ids(pg.run(pg.q.select("id").from_("u").where("name ILIKE", "Y%"))) == [2]
    q = pg.q.select("id").from_("u").where(Condition("name ~*", "^Z"))
    assert _ids(pg.run(q)) == [3]


def test_mysql_operators_are_rejected_before_reaching_postgresql(pg):
    for op in ("<=>", "REGEXP", "NOT REGEXP"):
        with pytest.raises(UnsupportedFeatureError, match="PostgreSQL"):
            pg.q.select("id").from_("u").where("name", "x", op)
    with pytest.raises(psycopg.Error):  # the fact behind it
        pg.execute("SELECT id FROM u WHERE name REGEXP 'x'")


# --- joins ------------------------------------------------------------------------------


def test_full_outer_join_returns_rows_from_both_sides(pg):
    pg.run(pg.q.insert_into("v").values({"id": 9, "k": 90}))  # a row only in v
    q = pg.q.select(func.count("*")).from_("u").join("v", "u.id = v.id", join_type="FULL OUTER")
    assert pg.run(q) == [(4,)]  # 1, 2 match; 3 only in u; 9 only in v


# --- JSON --------------------------------------------------------------------------------


def test_json_paths_use_hash_arrow_and_never_the_mysql_form(pg):
    q = pg.q.select(JSON("d").extract("a.c[1].b")).from_("u").where("id", 1)
    assert pg.run(q) == [("9",)]
    # sqlo never emits the MySQL path: PostgreSQL accepts it and silently returns NULL
    assert pg.execute("""SELECT d ->> '$.a.b' FROM u WHERE id = 1""") == [(None,)]
    assert pg.execute("""SELECT d #>> '{a,b}' FROM u WHERE id = 1""") == [("5",)]


def test_json_wildcards_are_rejected(pg):
    with pytest.raises(UnsupportedFeatureError, match="wildcard"):
        pg.q.select(JSON("d").extract("list[*]")).from_("u").build()


# --- window frames -------------------------------------------------------------------------


@pytest.mark.parametrize("unit", ["MICROSECOND", "SECOND", "MINUTE", "HOUR", "DAY", "WEEK", "MONTH", "YEAR"])
def test_every_interval_unit_runs(pg, unit):
    frame = Window.order_by("ts").range_between(f"INTERVAL 2 {unit} PRECEDING", "CURRENT ROW")
    assert len(pg.run(pg.q.select(func.sum("a").over(frame)).from_("u"))) == 3


def test_quarter_is_converted_to_months(pg):
    frame = Window.order_by("ts").range_between("INTERVAL 2 QUARTER PRECEDING", "CURRENT ROW")
    q = pg.q.select("id", func.sum("a").over(frame).as_("s")).from_("u").order_by("id")
    assert numbers(pg.run(q)) == [(1, 1), (2, 3), (3, 6)]
    with pytest.raises(psycopg.Error):  # the fact behind it
        pg.execute("SELECT SUM(a) OVER (ORDER BY ts RANGE BETWEEN INTERVAL '2 quarter' PRECEDING AND CURRENT ROW) FROM u")


# --- upsert ----------------------------------------------------------------------------------


def test_do_update_needs_the_conflict_columns_in_sqlo_and_in_postgresql(pg):
    with pytest.raises(ValueError, match="conflict column"):
        pg.q.insert_into("v").values({"id": 1, "k": 1}).on_conflict().do_update({"k": values_of("k")})
    with pytest.raises(psycopg.Error):  # the fact behind it
        pg.execute('INSERT INTO v (id, k) VALUES (1, 1) ON CONFLICT DO UPDATE SET k = EXCLUDED.k')


def test_do_nothing_works_without_the_conflict_columns(pg):
    pg.run(pg.q.insert_into("v").values({"id": 1, "k": 999}).on_conflict().do_nothing())
    assert pg.run(pg.q.select("k").from_("v").where("id", 1)) == [(10,)]


# --- what sqlo refuses before it reaches PostgreSQL ---------------------------------------------


def test_mysql_only_features_are_rejected(pg):
    with pytest.raises(UnsupportedFeatureError):
        pg.q.select("id").from_("u").force_index("i")
    with pytest.raises(UnsupportedFeatureError):
        pg.q.insert_into("v").values({"id": 1, "k": 1}).ignore()
    with pytest.raises(UnsupportedFeatureError):
        pg.q.insert_into("v").values({"id": 1, "k": 1}).on_duplicate_key_update({"k": 1})
    for method in ("join", "order_by", "limit"):
        for make in (pg.q.update, pg.q.delete_from):
            args = ("v", "u.id = v.id") if method == "join" else (("id",) if method == "order_by" else (1,))
            with pytest.raises(UnsupportedFeatureError):
                getattr(make("u"), method)(*args)


def test_the_postgresql_forms_that_replace_them_exist(pg):
    """UPDATE ... FROM and DELETE ... USING are what PostgreSQL has instead of JOIN."""
    assert pg.execute("UPDATE u SET a = 7 FROM v WHERE u.id = v.id AND u.id = 1") == 1
    assert pg.execute("DELETE FROM u USING v WHERE u.id = v.id AND u.id = 1") == 1
    with pytest.raises(psycopg.Error):
        pg.execute("UPDATE u INNER JOIN v ON u.id = v.id SET a = 7")


# --- PostgreSQL's own rules that portable code has to respect ---------------------------------------


def test_a_select_alias_cannot_be_used_in_having(pg):
    with pytest.raises(psycopg.Error, match="does not exist"):
        pg.execute('SELECT user_id, COUNT(*) AS n FROM o GROUP BY user_id HAVING n > 0')


def test_quoted_identifiers_are_case_sensitive(pg):
    pg.q.select("Id").from_("u").build()  # sqlo quotes exactly what it is given
    with pytest.raises(psycopg.Error):
        pg.run(pg.q.select("Id").from_("u"))
