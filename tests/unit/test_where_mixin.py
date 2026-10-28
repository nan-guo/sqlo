import pytest

from sqlo import Q
from sqlo.dialects.mysql import MySQLDialect
from sqlo.query.mixins import WhereClauseMixin


def _select():
    return Q.select("*").from_("t")


def _update():
    return Q.update("t").set({"x": 1})


def _delete():
    return Q.delete_from("t")


FACTORIES = [("select", _select), ("update", _update), ("delete", _delete)]


def _where_part(sql: str) -> str:
    return sql.split(" WHERE ", 1)[1]


# (method name, args) for every condition helper the mixin provides
HELPERS = [
    ("where_in", ("a", [1, 2])),
    ("or_where_in", ("a", [1, 2])),
    ("where_not_in", ("a", (1, 2))),
    ("or_where_not_in", ("a", (1, 2))),
    ("where_in", ("a", [])),
    ("where_not_in", ("a", [])),
    ("where_null", ("a",)),
    ("or_where_null", ("a",)),
    ("where_not_null", ("a",)),
    ("or_where_not_null", ("a",)),
    ("where_between", ("a", 1, 2)),
    ("or_where_between", ("a", 1, 2)),
    ("where_not_between", ("a", 1, 2)),
    ("or_where_not_between", ("a", 1, 2)),
    ("where_like", ("a", "x%")),
    ("or_where_like", ("a", "x%")),
    ("where_not_like", ("a", "x%")),
    ("or_where_not_like", ("a", "x%")),
    ("where", ("a", 1)),
    ("or_where", ("a", 1)),
]


@pytest.mark.parametrize("name, args", HELPERS)
def test_every_query_type_renders_the_helpers_identically(name, args):
    rendered = []
    for label, factory in FACTORIES:
        q = factory().where("z", 0)  # a leading condition so OR is visible
        sql, params = getattr(q, name)(*args).build()
        if label == "update":
            params = params[1:]  # the SET value comes first
        rendered.append((_where_part(sql), params))
    assert rendered[0] == rendered[1] == rendered[2]


@pytest.mark.parametrize("name, args", HELPERS)
def test_helpers_return_the_same_query(name, args):
    for _, factory in FACTORIES:
        q = factory()
        assert getattr(q, name)(*args) is q


@pytest.mark.parametrize("name", ["where_like", "or_where_like", "where_not_like", "or_where_not_like"])
@pytest.mark.parametrize("label, factory", FACTORIES)
def test_like_without_a_pattern_is_rejected_everywhere(name, label, factory):
    with pytest.raises(ValueError, match="pattern"):
        getattr(factory(), name)("a", None)


@pytest.mark.parametrize("name", ["where_in", "or_where_in", "where_not_in", "or_where_not_in"])
@pytest.mark.parametrize("values", [[], [1]])
@pytest.mark.parametrize("label, factory", FACTORIES)
def test_in_helpers_validate_the_column_even_for_an_empty_list(name, values, label, factory):
    with pytest.raises(ValueError, match="Invalid identifier"):
        getattr(factory(), name)("a; DROP TABLE x", values)


def test_empty_in_constants_are_unchanged():
    assert _where_part(_select().where_in("a", []).build()[0]) == "FALSE"
    assert _where_part(_select().where_not_in("a", []).build()[0]) == "TRUE"


def test_a_mixin_user_without_wheres_fails_loudly_instead_of_doing_nothing():
    class Broken(WhereClauseMixin):
        _dialect = MySQLDialect()
        _ph = "%s"

    for call in (
        lambda: Broken().where_null("a"),
        lambda: Broken().where_in("a", [1]),
        lambda: Broken().where_between("a", 1, 2),
        lambda: Broken().where_like("a", "x"),
        lambda: Broken().or_where("a", 1),
    ):
        with pytest.raises(AttributeError):
            call()
