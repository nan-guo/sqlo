import pytest

from sqlo import Condition, Q, UnsupportedFeatureError
from sqlo.dialects.base import Dialect
from sqlo.dialects.mysql import MySQLDialect
from sqlo.query.delete import DeleteQuery
from sqlo.query.insert import InsertQuery
from sqlo.query.select import SelectQuery
from sqlo.query.update import UpdateQuery
from sqlo.security import validate_operator


class PlainDialect(Dialect):
    """Only the portable features: no MySQL extras."""

    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


PLAIN = PlainDialect()
MYSQL = MySQLDialect()


def _select(dialect=PLAIN):
    return SelectQuery("*", dialect=dialect).from_("t")


# --- the error type --------------------------------------------------------


def test_unsupported_feature_error_is_a_value_error_with_a_clear_message():
    err = UnsupportedFeatureError("Plain", "Index hints", "Use another way.")
    assert isinstance(err, ValueError)
    assert (
        str(err)
        == "Index hints is not supported by the Plain dialect. Use another way."
    )
    assert (err.dialect, err.feature) == ("Plain", "Index hints")


def test_dialect_names():
    assert PLAIN.name == "Plain"
    assert MYSQL.name == "MySQL"


# --- features a portable dialect does not have -----------------------------


@pytest.mark.parametrize("method", ["force_index", "use_index", "ignore_index"])
def test_index_hints_are_rejected_when_called(method):
    q = _select()
    with pytest.raises(UnsupportedFeatureError, match="Index hints"):
        getattr(q, method)("idx")
    assert q.build()[0] == 'SELECT * FROM "t"'


def test_optimizer_hints_are_rejected_when_called():
    q = _select()
    with pytest.raises(UnsupportedFeatureError, match="Optimizer hints"):
        q.optimizer_hint("MAX_EXECUTION_TIME(1)")
    assert q.build()[0] == 'SELECT * FROM "t"'


def test_json_paths_are_rejected():
    from sqlo import JSON

    with pytest.raises(UnsupportedFeatureError, match="JSON"):
        SelectQuery(JSON("d").extract("a"), dialect=PLAIN).from_("t").build()
    with pytest.raises(UnsupportedFeatureError, match="JSON"):
        _select().where(JSON("d").extract("a"), 1)


def test_insert_ignore_and_on_duplicate_key_update_are_rejected():
    q = InsertQuery("t", dialect=PLAIN).values({"a": 1})
    with pytest.raises(UnsupportedFeatureError, match="INSERT IGNORE"):
        q.ignore()
    with pytest.raises(UnsupportedFeatureError, match="ON DUPLICATE KEY UPDATE"):
        q.on_duplicate_key_update({"a": 2})
    assert q.build()[0] == 'INSERT INTO "t" ("a") VALUES (?)'


@pytest.mark.parametrize("make", [UpdateQuery, DeleteQuery])
def test_update_and_delete_joins_are_rejected(make):
    q = make("t", dialect=PLAIN)
    with pytest.raises(UnsupportedFeatureError, match="JOIN"):
        q.join("v", "t.id = v.id")
    with pytest.raises(UnsupportedFeatureError, match="JOIN"):
        q.left_join("v", "t.id = v.id")


@pytest.mark.parametrize("make", [UpdateQuery, DeleteQuery])
def test_update_and_delete_order_by_and_limit_are_rejected(make):
    q = make("t", dialect=PLAIN)
    with pytest.raises(UnsupportedFeatureError, match="ORDER BY"):
        q.order_by("id")
    with pytest.raises(UnsupportedFeatureError, match="LIMIT"):
        q.limit(1)


def test_update_and_delete_without_the_extras_still_work():
    sql, _ = UpdateQuery("t", dialect=PLAIN).set({"a": 1}).where("id", 1).build()
    assert sql == 'UPDATE "t" SET "a" = ? WHERE "id" = ?'
    sql, _ = DeleteQuery("t", dialect=PLAIN).where("id", 1).build()
    assert sql == 'DELETE FROM "t" WHERE "id" = ?'


# --- join types --------------------------------------------------------------


@pytest.mark.parametrize(
    "join_type", ["INNER", "LEFT", "RIGHT", "CROSS", "left outer", "RIGHT OUTER"]
)
def test_portable_join_types_work_everywhere(join_type):
    for dialect in (PLAIN, MYSQL):
        _select(dialect).join("v", "t.id = v.id", join_type=join_type)


@pytest.mark.parametrize("join_type", ["FULL", "FULL OUTER", "full outer"])
def test_full_join_is_rejected_by_mysql_and_portable_dialects(join_type):
    for dialect, name in ((MYSQL, "MySQL"), (PLAIN, "Plain")):
        with pytest.raises(UnsupportedFeatureError, match=f"FULL.*{name}"):
            _select(dialect).join("v", "t.id = v.id", join_type=join_type)


def test_a_made_up_join_type_is_an_invalid_value_not_an_unsupported_feature():
    with pytest.raises(ValueError) as info:
        _select().join("v", "t.id = v.id", join_type="WEIRD")
    assert not isinstance(info.value, UnsupportedFeatureError)


# --- operators: checked when the query is built for a dialect ---------------


@pytest.mark.parametrize("op", ["<=>", "REGEXP", "NOT REGEXP"])
def test_mysql_operators_are_rejected_by_a_portable_dialect(op):
    with pytest.raises(UnsupportedFeatureError, match="Plain"):
        _select().where(f"a {op}", "x")
    _select(MYSQL).where(f"a {op}", "x")  # MySQL accepts it


@pytest.mark.parametrize(
    "op", ["=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE"]
)
def test_portable_operators_work_in_every_dialect(op):
    for dialect in (PLAIN, MYSQL):
        _select(dialect).where("a", 1, op)


def test_condition_checks_the_operator_for_the_dialect_it_is_rendered_with():
    cond = Condition("a REGEXP", "x")  # built without knowing the dialect
    assert cond.build(MYSQL)[0] == "`a` REGEXP %s"
    with pytest.raises(UnsupportedFeatureError, match="REGEXP"):
        cond.build(PLAIN)
    with pytest.raises(UnsupportedFeatureError, match="REGEXP"):
        _select().where(cond)


def test_an_unknown_operator_is_still_an_invalid_value():
    with pytest.raises(ValueError) as info:
        validate_operator("= 1 OR 1=1 --", MYSQL)
    assert not isinstance(info.value, UnsupportedFeatureError)
    with pytest.raises(ValueError):
        Condition("a", 1, "= 1 OR 1=1 --")


def test_validate_operator_works_without_a_dialect():
    assert validate_operator("not   like") == "NOT LIKE"
    assert validate_operator("<=>") == "<=>"


# --- MySQL keeps all of it ---------------------------------------------------


def test_mysql_supports_its_extras():
    assert (
        "FORCE INDEX (`i`)" in SelectQuery("*").from_("t").force_index("i").build()[0]
    )
    assert (
        "/*+ X(1) */" in SelectQuery("*").from_("t").optimizer_hint("X(1)").build()[0]
    )
    assert (
        Q.insert_into("t")
        .values({"a": 1})
        .ignore()
        .build()[0]
        .startswith("INSERT IGNORE")
    )
    assert (
        "ON DUPLICATE KEY UPDATE"
        in (
            Q.insert_into("t")
            .values({"a": 1})
            .on_duplicate_key_update({"a": 2})
            .build()[0]
        )
    )
    assert "LIMIT 1" in Q.update("t").set({"a": 1}).where("id", 1).limit(1).build()[0]
    assert "ORDER BY" in Q.delete_from("t").where("id", 1).order_by("id").build()[0]
    assert (
        Q.delete_from("t")
        .join("v", "t.id = v.id")
        .where("t.id", 1)
        .build()[0]
        .startswith("DELETE `t` FROM `t`")
    )


# --- a custom dialect can switch features on ---------------------------------


def test_a_custom_dialect_can_enable_features():
    class Rich(PlainDialect):
        supports_dml_order_limit = True
        supports_dml_join = True
        extra_operators = frozenset({"<=>"})

        def index_hint(self, kind, quoted_indexes):
            return f" USING {kind} ({quoted_indexes})"

    rich = Rich()
    sql, _ = (
        UpdateQuery("t", dialect=rich).set({"a": 1}).where("id", 1).limit(2).build()
    )
    assert sql.endswith("LIMIT 2")
    UpdateQuery("t", dialect=rich).join("v", "t.id = v.id")
    sql, _ = _select(rich).where("a <=>", 1).force_index("i").build()
    assert sql == 'SELECT * FROM "t" USING FORCE ("i") WHERE "a" <=> ?'


def test_defaults_of_the_base_dialect_are_the_portable_ones():
    assert PLAIN.extra_operators == frozenset()
    assert PLAIN.supports_insert_ignore is False
    assert PLAIN.supports_on_duplicate_key is False
    assert PLAIN.supports_dml_join is False
    assert PLAIN.supports_dml_order_limit is False
    assert "FULL" not in PLAIN.join_types and "INNER" in PLAIN.join_types
