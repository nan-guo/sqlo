import pytest

from sqlo import Q

BAD_JOIN_TYPES = [
    "INNER JOIN w; DROP TABLE x;--",
    "LEFT; DROP",
    "WEIRD",
    "",
    "INNER OUTER",
]

BAD_TABLE_REFS = [
    "v x; DROP TABLE x",
    "v; DROP TABLE x",
    "v x y z",
    "v a.b",
    "v AS a; DROP",
    "v AS",
    "",
    " ",
]

BAD_ALIASES = ["a; DROP TABLE x", "a b", "a.b", "1a", "", "a`b"]


def _select():
    return Q.select("*").from_("u")


@pytest.mark.parametrize("join_type", BAD_JOIN_TYPES)
def test_select_join_type_rejected(join_type):
    with pytest.raises(ValueError):
        _select().join("v", "u.id = v.id", join_type=join_type)


@pytest.mark.parametrize("join_type", BAD_JOIN_TYPES)
def test_update_delete_join_type_rejected(join_type):
    with pytest.raises(ValueError):
        Q.update("u").join("v", "u.id = v.id", join_type=join_type)
    with pytest.raises(ValueError):
        Q.delete_from("u").join("v", "u.id = v.id", join_type=join_type)


@pytest.mark.parametrize("join_type", ["inner", "Left", "RIGHT", "cross", "left outer"])
def test_valid_join_types_accepted(join_type):
    sql, _ = _select().join("v", "u.id = v.id", join_type=join_type).build()
    assert f"{join_type.upper()} JOIN `v`" in sql


@pytest.mark.parametrize("table", BAD_TABLE_REFS)
def test_select_join_table_rejected(table):
    with pytest.raises(ValueError):
        _select().join(table, "u.id = v.id")


@pytest.mark.parametrize("table", BAD_TABLE_REFS)
def test_update_delete_join_table_rejected(table):
    with pytest.raises(ValueError):
        Q.update("u").join(table, "u.id = v.id")
    with pytest.raises(ValueError):
        Q.delete_from("u").join(table, "u.id = v.id")


@pytest.mark.parametrize(
    "table, rendered",
    [
        ("orders", "`orders`"),
        ("orders o", "`orders` o"),
        ("orders AS o", "`orders` AS o"),
        ("db.orders o", "`db`.`orders` o"),
    ],
)
def test_valid_join_tables_accepted(table, rendered):
    sql, _ = _select().left_join(table, "u.id = o.uid").build()
    assert f"LEFT JOIN {rendered} ON" in sql


def test_update_delete_valid_join_still_works():
    sql, _ = (
        Q.update("u").set({"a": 1}).join("v x", "u.id = x.id").where("u.id", 1).build()
    )
    assert "INNER JOIN `v` x ON u.id = x.id" in sql
    sql, _ = Q.delete_from("u").join("v x", "u.id = x.id").where("u.id", 1).build()
    assert "INNER JOIN `v` x ON u.id = x.id" in sql


@pytest.mark.parametrize("alias", BAD_ALIASES)
def test_from_alias_rejected(alias):
    with pytest.raises(ValueError):
        Q.select("*").from_("u", alias)


@pytest.mark.parametrize("alias", BAD_ALIASES)
def test_as_alias_rejected(alias):
    with pytest.raises(ValueError):
        Q.select("*").from_("u").as_(alias)


@pytest.mark.parametrize("alias", BAD_ALIASES)
def test_subquery_from_alias_rejected(alias):
    sub = Q.select("*").from_("u")
    with pytest.raises(ValueError):
        Q.select("*").from_(sub, alias)


def test_valid_aliases_unchanged():
    sql, _ = Q.select("*").from_("users", "u_1").build()
    assert sql == "SELECT * FROM `users` u_1"
    sub = Q.select("id").from_("users")
    sql, _ = Q.select("*").from_(sub, alias="active").build()
    assert sql == "SELECT * FROM (SELECT `id` FROM `users`) AS active"


def test_subquery_join_renders_parenthesized_with_params_in_order():
    sub = Q.select("user_id").from_("orders").where("total >", 10).as_("lo")
    sql, params = (
        Q.select("*")
        .from_("users", "u")
        .join(sub, "lo.user_id = u.id")
        .where("u.active", True)
        .build()
    )
    assert " INNER JOIN (SELECT `user_id` FROM `orders`" in sql
    assert ") AS lo ON lo.user_id = u.id WHERE `u`.`active` = %s" in sql
    assert params == (10, True)


def test_subquery_join_requires_alias():
    sub = Q.select("user_id").from_("orders")
    with pytest.raises(ValueError):
        _select().join(sub, "x = y")
