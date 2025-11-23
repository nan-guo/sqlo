"""
Tests for DELETE queries.

Coverage:
- Basic DELETE
- DELETE with WHERE clauses
- DELETE with LIMIT
- DELETE with ORDER BY
- Error handling
"""

import pytest

from sqlo import Condition, Q, Raw


def test_delete_basic():
    """Basic DELETE with WHERE"""
    q = Q.delete_from("users").where("id", 1)
    sql, params = q.build()
    assert sql == "DELETE FROM `users` WHERE `id` = ?"
    assert params == (1,)


def test_delete_with_limit_and_order():
    """DELETE with LIMIT and ORDER BY"""
    query = (
        Q.delete_from("logs")
        .where("created_at <", "2020-01-01")
        .order_by("created_at")
        .limit(1000)
    )
    sql, params = query.build()
    assert "DELETE FROM `logs`" in sql
    assert "ORDER BY `created_at` ASC" in sql
    assert "LIMIT 1000" in sql
    assert params == ("2020-01-01",)


def test_delete_where_raw():
    """DELETE with Raw WHERE clause"""
    query = Q.delete_from("logs").where(
        Raw("created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)", [])
    )
    sql, _ = query.build()
    assert "WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)" in sql


def test_delete_where_condition():
    """DELETE with Condition object"""
    cond = Condition("status", "inactive") | Condition("banned", True)
    query = Q.delete_from("users").where(cond)
    sql, params = query.build()
    assert params == ("inactive", True)


def test_delete_without_table():
    """DELETE without table should raise error"""
    from sqlo.query.delete import DeleteQuery

    query = DeleteQuery("")
    query._table = None
    with pytest.raises(ValueError, match="No table specified"):
        query.build()
