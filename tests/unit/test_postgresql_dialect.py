import pytest

from sqlo import JSON, Condition, UnsupportedFeatureError, Window, func
from sqlo.dialects.mysql import MySQLDialect
from sqlo.dialects.postgresql import PostgreSQLDialect
from sqlo.query.delete import DeleteQuery
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery
from sqlo.query.update import UpdateQuery

PG = PostgreSQLDialect()


def _s(*columns):
    return SelectQuery(*columns, dialect=PG)


# --- basics ------------------------------------------------------------------


def test_identity():
    assert PG.name == "PostgreSQL"
    assert PG.quote_char == '"'
    assert PG.parameter_placeholder() == "%s"
    assert PG.quote("users") == '"users"'
    assert PG.quote("public.users") == '"public"."users"'


def test_identifier_validation_still_applies():
    with pytest.raises(ValueError, match="Invalid identifier"):
        PG.quote('a"; DROP TABLE x;--')


def test_select_where_order_limit():
    sql, params = (
        _s("id", "name")
        .from_("users", "u")
        .where("u.active", True)
        .where_in("u.id", [1, 2])
        .order_by("-id")
        .limit(10)
        .offset(5)
        .build()
    )
    assert sql == (
        'SELECT "id", "name" FROM "users" u WHERE "u"."active" = %s '
        'AND "u"."id" IN (%s, %s) ORDER BY "id" DESC LIMIT 10 OFFSET 5'
    )
    assert params == (True, 1, 2)


def test_insert_update_delete():
    assert InsertQuery("t", dialect=PG).values({"a": 1, "b": 2}).build() == (
        'INSERT INTO "t" ("a", "b") VALUES (%s, %s)',
        (1, 2),
    )
    assert UpdateQuery("t", dialect=PG).set({"a": 1}).where("id", 2).build() == (
        'UPDATE "t" SET "a" = %s WHERE "id" = %s',
        (1, 2),
    )
    assert DeleteQuery("t", dialect=PG).where("id", 2).build() == (
        'DELETE FROM "t" WHERE "id" = %s',
        (2,),
    )


def test_subqueries_unions_and_ctes_render_with_postgresql_quoting():
    sub = SelectQuery("id", dialect=PG).from_("v").where("k", 9)
    sql, params = _s("*").from_("u").where_in("id", sub).build()
    assert (
        sql == 'SELECT * FROM "u" WHERE "id" IN (SELECT "id" FROM "v" WHERE "k" = %s)'
    )
    assert params == (9,)

    union = _s("id").from_("u").union(SelectQuery("id", dialect=PG).from_("v").limit(1))
    assert (
        union.build()[0] == 'SELECT "id" FROM "u" UNION (SELECT "id" FROM "v" LIMIT 1)'
    )

    cte = SelectQuery("id", dialect=PG).from_("u").where("a", 1)
    sql, _ = _s("*").from_("c").with_(cte, "c").build()
    assert sql == 'WITH "c" AS (SELECT "id" FROM "u" WHERE "a" = %s) SELECT * FROM "c"'


def test_conditions_render_with_postgresql_quoting():
    cond = Condition("a", 1) | Condition.in_("b", [1, 2])
    sql, params = _s("*").from_("t").where(cond).build()
    assert sql == 'SELECT * FROM "t" WHERE (("a" = %s OR "b" IN (%s, %s)))'
    assert params == (1, 1, 2)


# --- joins --------------------------------------------------------------------


@pytest.mark.parametrize("join_type", ["FULL", "FULL OUTER", "full outer"])
def test_full_join_is_supported(join_type):
    sql, _ = _s("*").from_("u").join("v", "u.id = v.id", join_type=join_type).build()
    assert f'{join_type.upper()} JOIN "v" ON u.id = v.id' in sql


def test_portable_joins_still_work():
    for join_type in ("INNER", "LEFT", "RIGHT", "CROSS", "LEFT OUTER"):
        _s("*").from_("u").join("v", "u.id = v.id", join_type=join_type)


# --- operators ----------------------------------------------------------------


@pytest.mark.parametrize(
    "op",
    [
        "~",
        "~*",
        "!~",
        "!~*",
        "ILIKE",
        "NOT ILIKE",
        "IS DISTINCT FROM",
        "IS NOT DISTINCT FROM",
    ],
)
def test_postgresql_operators(op):
    sql, params = _s("*").from_("t").where("name", "x", op).build()
    assert sql == f'SELECT * FROM "t" WHERE "name" {op} %s'
    assert params == ("x",)


def test_postgresql_operators_in_the_spaced_form_and_in_conditions():
    sql, _ = _s("*").from_("t").where("name ILIKE", "x%").build()
    assert sql == 'SELECT * FROM "t" WHERE "name" ILIKE %s'
    assert (
        _s("*")
        .from_("t")
        .where(Condition("name ~*", "^x"))
        .build()[0]
        .endswith('WHERE ("name" ~* %s)')
    )
    assert Condition("a IS NOT DISTINCT FROM", 1).build(PG) == (
        '"a" IS NOT DISTINCT FROM %s',
        (1,),
    )


@pytest.mark.parametrize("op", ["<=>", "REGEXP", "NOT REGEXP"])
def test_mysql_operators_are_rejected(op):
    with pytest.raises(UnsupportedFeatureError, match="PostgreSQL"):
        _s("*").from_("t").where("a", "x", op)


@pytest.mark.parametrize("op", ["~", "ILIKE", "IS DISTINCT FROM"])
def test_postgresql_operators_are_rejected_by_mysql(op):
    with pytest.raises(UnsupportedFeatureError, match="MySQL"):
        SelectQuery("*", dialect=MySQLDialect()).from_("t").where("a", "x", op)
    cond = Condition(f"a {op}", "x")
    assert cond.build(PG)[0].startswith('"a" ')
    with pytest.raises(UnsupportedFeatureError, match="MySQL"):
        cond.build(MySQLDialect())


def test_injection_through_operators_is_still_rejected():
    with pytest.raises(ValueError):
        _s("*").from_("t").where("a", 1, "~ 1 OR 1=1 --")


# --- JSON ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("name", """"d" ->> 'name'"""),
        ("a.b", """"d" #>> '{a,b}'"""),
        ("a[0].b", """"d" #>> '{a,0,b}'"""),
        ("a.c[1].b", """"d" #>> '{a,c,1,b}'"""),
        ("list[1]", """"d" #>> '{list,1}'"""),
        ("[0]", '"d" ->> 0'),
        ("[2].x", """"d" #>> '{2,x}'"""),
    ],
)
def test_json_paths(path, expected):
    sql, _ = _s(JSON("d").extract(path)).from_("t").build()
    assert sql == f'SELECT {expected} FROM "t"'


def test_json_path_in_where_and_with_an_alias():
    sql, params = _s("*").from_("t").where(JSON("d").extract("a.b"), "5").build()
    assert sql == """SELECT * FROM "t" WHERE "d" #>> '{a,b}' = %s"""
    assert params == ("5",)
    sql, _ = _s(JSON("d").extract("a.b").as_("x")).from_("t").build()
    assert sql == """SELECT "d" #>> '{a,b}' AS "x" FROM "t\""""


def test_the_mysql_path_form_is_never_emitted():
    """`->> '$.a'` runs on PostgreSQL but silently returns NULL."""
    for path in ("a", "a.b", "a[0]", "[0]"):
        sql, _ = _s(JSON("d").extract(path)).from_("t").build()
        assert "$" not in sql


@pytest.mark.parametrize("path", ["tags[*]", "*", "a.*", "a[*].b"])
def test_json_wildcards_are_rejected(path):
    with pytest.raises(UnsupportedFeatureError, match="wildcard"):
        _s(JSON("d").extract(path)).from_("t").build()
    with pytest.raises(UnsupportedFeatureError, match="wildcard"):
        _s("*").from_("t").where(JSON("d").extract(path), 1)


# --- window frames --------------------------------------------------------------


def _frame(start, end, kind="range_between"):
    window = getattr(Window.order_by("ts"), kind)(start, end)
    sql, _ = _s(func.sum("a").over(window)).from_("t").build()
    return sql


def test_interval_bounds_are_quoted_for_postgresql():
    assert _frame("INTERVAL 7 DAY PRECEDING", "CURRENT ROW").endswith(
        """RANGE BETWEEN INTERVAL '7 day' PRECEDING AND CURRENT ROW) FROM "t\""""
    )
    assert "INTERVAL '2 hour' FOLLOWING" in _frame(
        "CURRENT ROW", "INTERVAL 2 HOUR FOLLOWING"
    )


def test_quarter_is_converted_because_postgresql_has_no_such_unit():
    assert "INTERVAL '6 month' PRECEDING" in _frame(
        "INTERVAL 2 QUARTER PRECEDING", "CURRENT ROW"
    )


@pytest.mark.parametrize(
    "unit", ["MICROSECOND", "SECOND", "MINUTE", "HOUR", "DAY", "WEEK", "MONTH", "YEAR"]
)
def test_every_other_unit_is_passed_through_in_lower_case(unit):
    assert f"INTERVAL '3 {unit.lower()}' PRECEDING" in _frame(
        f"INTERVAL 3 {unit} PRECEDING", "CURRENT ROW"
    )


def test_non_interval_bounds_are_unchanged():
    assert (
        _frame("UNBOUNDED PRECEDING", "CURRENT ROW", "rows_between").count(
            "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        )
        == 1
    )
    assert "ROWS BETWEEN 2 PRECEDING AND 1 FOLLOWING" in _frame(
        "2 PRECEDING", "1 FOLLOWING", "rows_between"
    )


def test_the_same_window_renders_per_dialect():
    window = Window.order_by("ts").range_between(
        "INTERVAL 7 DAY PRECEDING", "CURRENT ROW"
    )
    assert "INTERVAL 7 DAY PRECEDING" in window.build(MySQLDialect())
    assert "INTERVAL '7 day' PRECEDING" in window.build(PG)


# --- features PostgreSQL does not have ------------------------------------------


def test_mysql_only_features_raise():
    q = _s("*").from_("t")
    with pytest.raises(UnsupportedFeatureError, match="Index hints"):
        q.force_index("i")
    with pytest.raises(UnsupportedFeatureError, match="Optimizer hints"):
        q.optimizer_hint("MAX_EXECUTION_TIME(1)")
    ins = InsertQuery("t", dialect=PG).values({"a": 1})
    with pytest.raises(UnsupportedFeatureError, match="INSERT IGNORE"):
        ins.ignore()
    with pytest.raises(UnsupportedFeatureError, match="ON DUPLICATE KEY UPDATE"):
        ins.on_duplicate_key_update({"a": 1})


@pytest.mark.parametrize("make", [UpdateQuery, DeleteQuery])
def test_update_and_delete_extras_raise(make):
    q = make("t", dialect=PG)
    with pytest.raises(UnsupportedFeatureError, match="JOIN"):
        q.join("v", "t.id = v.id")
    with pytest.raises(UnsupportedFeatureError, match="ORDER BY"):
        q.order_by("id")
    with pytest.raises(UnsupportedFeatureError, match="LIMIT"):
        q.limit(1)


def test_mysql_output_is_untouched_by_the_new_dialect():
    mysql = MySQLDialect()
    assert SelectQuery(JSON("d").extract("a.b"), dialect=mysql).from_("t").build()[
        0
    ] == ("SELECT `d`->>'$.a.b' FROM `t`")
    window = Window.order_by("ts").range_between(
        "INTERVAL 7 DAY PRECEDING", "CURRENT ROW"
    )
    assert window.build(mysql).endswith(
        "RANGE BETWEEN INTERVAL 7 DAY PRECEDING AND CURRENT ROW"
    )
    assert PG.extra_operators.isdisjoint(mysql.extra_operators)


def test_top_level_exports():
    import sqlo

    assert sqlo.PostgreSQLDialect is PostgreSQLDialect
    assert sqlo.MySQLDialect is MySQLDialect
