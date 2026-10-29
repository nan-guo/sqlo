import pytest

from sqlo import (
    Condition,
    MySQLDialect,
    PostgreSQLDialect,
    Q,
    QueryFactory,
    Raw,
    UnsupportedFeatureError,
    values_of,
)
from sqlo.query.delete import DeleteQuery
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery
from sqlo.query.update import UpdateQuery

PG = PostgreSQLDialect()
MYSQL = MySQLDialect()
pg = Q.using(PG)
mysql = Q.using(MYSQL)


# --- the factory -----------------------------------------------------------------


def test_using_returns_a_factory_bound_to_the_dialect():
    assert isinstance(pg, QueryFactory)
    assert pg.dialect is PG


def test_factory_builds_every_query_type_in_its_dialect():
    sql, params = pg.select("id").from_("u").where("a", 1).build()
    assert sql == 'SELECT "id" FROM "u" WHERE "a" = %s'
    assert params == (1,)
    assert (
        pg.insert_into("u").values({"a": 1}).build()[0]
        == 'INSERT INTO "u" ("a") VALUES (%s)'
    )
    assert pg.update("u").set({"a": 1}).where("id", 2).build()[0] == (
        'UPDATE "u" SET "a" = %s WHERE "id" = %s'
    )
    assert (
        pg.delete_from("u").where("id", 2).build()[0]
        == 'DELETE FROM "u" WHERE "id" = %s'
    )


def test_factory_queries_have_the_expected_types():
    assert isinstance(pg.select("a"), SelectQuery)
    assert isinstance(pg.insert_into("t"), InsertQuery)
    assert isinstance(pg.update("t"), UpdateQuery)
    assert isinstance(pg.delete_from("t"), DeleteQuery)


def test_select_defaults_to_all_columns_and_accepts_a_list():
    assert pg.select().from_("t").build()[0] == 'SELECT * FROM "t"'
    assert pg.select(["a", "b"]).from_("t").build()[0] == 'SELECT "a", "b" FROM "t"'


def test_raw_is_available_on_the_factory():
    raw = pg.raw("a = %s", [1])
    assert isinstance(raw, Raw)
    assert (raw.sql, raw.params) == ("a = %s", [1])


def test_the_two_dialects_can_be_used_side_by_side():
    assert mysql.select("id").from_("u").build()[0] == "SELECT `id` FROM `u`"
    assert pg.select("id").from_("u").build()[0] == 'SELECT "id" FROM "u"'


def test_a_factory_ignores_the_global_default_dialect():
    original = Q.get_dialect()
    try:
        Q.set_dialect(PG)
        assert mysql.select("id").from_("u").build()[0] == "SELECT `id` FROM `u`"
        assert Q.select("id").from_("u").build()[0] == 'SELECT "id" FROM "u"'
    finally:
        Q.set_dialect(original)


def test_using_does_not_change_the_global_default_dialect():
    before = Q.get_dialect()
    Q.using(PG)
    assert Q.get_dialect() is before


def test_a_factory_can_be_reused_for_independent_queries():
    a = pg.select("id").from_("u").where("a", 1)
    b = pg.select("id").from_("u").where("b", 2)
    assert a.build()[0].endswith('WHERE "a" = %s')
    assert b.build()[0].endswith('WHERE "b" = %s')


def test_dialect_features_follow_the_factory():
    with pytest.raises(UnsupportedFeatureError, match="PostgreSQL"):
        pg.select("id").from_("u").force_index("i")
    assert "FORCE INDEX" in mysql.select("id").from_("u").force_index("i").build()[0]
    sql, _ = (
        pg.insert_into("u")
        .values({"id": 1, "n": "x"})
        .on_conflict("id")
        .do_update({"n": values_of("n")})
        .build()
    )
    assert sql.endswith('ON CONFLICT ("id") DO UPDATE SET "n" = EXCLUDED."n"')


@pytest.mark.parametrize(
    "bad", [PostgreSQLDialect, MySQLDialect, None, "postgresql", 1]
)
def test_using_needs_a_dialect_instance(bad):
    with pytest.raises(TypeError, match="Dialect"):
        Q.using(bad)


def test_the_error_says_to_pass_an_instance_for_a_class():
    with pytest.raises(TypeError, match=r"PostgreSQLDialect\(\)"):
        Q.using(PostgreSQLDialect)


# --- nested queries must use the same dialect ---------------------------------


def _mysql_sub():
    return mysql.select("id").from_("v").where("k", 1)


def _outer():
    return pg.select("*").from_("u")


def test_a_subquery_from_another_dialect_is_rejected_everywhere():
    sub = _mysql_sub()
    with pytest.raises(ValueError, match="dialect"):
        _outer().where_in("id", sub).build()
    with pytest.raises(ValueError, match="dialect"):
        pg.select("*").from_(sub.as_("s")).build()
    with pytest.raises(ValueError, match="dialect"):
        _outer().join(sub.as_("s"), "s.id = u.id").build()
    with pytest.raises(ValueError, match="dialect"):
        _outer().union(sub).build()
    with pytest.raises(ValueError, match="dialect"):
        _outer().with_(sub, "c").build()
    with pytest.raises(ValueError, match="dialect"):
        pg.insert_into("t").from_select(["id"], sub).build()
    with pytest.raises(ValueError, match="dialect"):
        pg.update("u").set({"a": sub}).where("id", 1).build()
    with pytest.raises(ValueError, match="dialect"):
        _outer().where(Condition.exists(sub)).build()


def test_the_message_names_both_dialects():
    with pytest.raises(ValueError, match="MySQL dialect.*PostgreSQL dialect"):
        _outer().where_in("id", _mysql_sub()).build()


def test_a_subquery_from_the_same_dialect_is_fine():
    sub = pg.select("id").from_("v").where("k", 1)
    sql, params = _outer().where_in("id", sub).build()
    assert (
        sql == 'SELECT * FROM "u" WHERE "id" IN (SELECT "id" FROM "v" WHERE "k" = %s)'
    )
    assert params == (1,)


def test_two_instances_of_the_same_dialect_class_are_compatible():
    sub = Q.using(PostgreSQLDialect()).select("id").from_("v")
    sql, _ = _outer().where_in("id", sub).build()
    assert sql == 'SELECT * FROM "u" WHERE "id" IN (SELECT "id" FROM "v")'


def test_the_global_default_and_an_explicit_mysql_factory_are_compatible():
    sub = Q.select("id").from_("v")
    sql, _ = mysql.select("*").from_("u").where_in("id", sub).build()
    assert sql == "SELECT * FROM `u` WHERE `id` IN (SELECT `id` FROM `v`)"
