"""Tests for JSON field support."""

from sqlo import Q
from sqlo.expressions import JSON


def test_json_select():
    """Test JSON field extraction in SELECT."""
    q = Q.select("id", JSON("data").extract("name").as_("name")).from_("users")
    sql, params = q.build()

    assert "SELECT `id`, `data`->>'$.name' AS `name`" in sql
    assert "FROM `users`" in sql
    assert params == ()


def test_json_where():
    """Test JSON field filtering in WHERE."""
    q = Q.select("*").from_("users").where(JSON("data").extract("age"), 18, ">")
    sql, params = q.build()

    assert "WHERE `data`->>'$.age' > %s" in sql
    assert params == (18,)


def test_json_nested_path():
    """Test nested JSON path extraction."""
    q = Q.select(JSON("metadata").extract("user.preferences.theme").as_("theme")).from_(
        "settings"
    )
    sql, _ = q.build()

    assert "`metadata`->>'$.user.preferences.theme' AS `theme`" in sql


def test_json_multiple_extractions():
    """Test multiple JSON extractions in same query."""
    q = Q.select(
        "id",
        JSON("data").extract("name").as_("name"),
        JSON("data").extract("email").as_("email"),
    ).from_("users")
    sql, _ = q.build()

    assert "`data`->>'$.name' AS `name`" in sql
    assert "`data`->>'$.email' AS `email`" in sql
