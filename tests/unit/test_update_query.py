import pytest

from sqlo import Condition, Q, Raw


def test_update_basic():
    """Basic UPDATE with WHERE"""
    q = Q.update("users").set({"active": True}).where("id", 1)
    sql, params = q.build()
    assert sql == "UPDATE `users` SET `active` = %s WHERE `id` = %s"
    assert params == (True, 1)


def test_update_multiple_columns():
    """UPDATE multiple columns"""
    q = (
        Q.update("users")
        .set({"active": True, "verified": False})
        .where("id", 1)
    )
    sql, params = q.build()
    assert "SET `active` = %s, `verified` = %s" in sql
    assert params == (True, False, 1)


def test_update_with_limit_and_order():
    """UPDATE with LIMIT and ORDER BY"""
    query = (
        Q.update("users")
        .set({"status": "inactive"})
        .where("last_login <", "2020-01-01")
        .order_by("-created_at")
        .limit(100)
    )
    sql, params = query.build()
    assert "UPDATE `users` SET `status` = %s" in sql
    assert "ORDER BY `created_at` DESC" in sql
    assert "LIMIT 100" in sql
    assert params == ("inactive", "2020-01-01")


def test_update_where_raw():
    """UPDATE with Raw WHERE clause"""
    query = (
        Q.update("users")
        .set({"status": "active"})
        .where(Raw("DATE(created_at) = CURDATE()", []))
    )
    sql, params = query.build()
    assert "WHERE DATE(created_at) = CURDATE()" in sql
    assert params == ("active",)


def test_update_where_condition():
    """UPDATE with Condition object"""
    cond = Condition("age >", 18) & Condition("country", "US")
    query = Q.update("users").set({"verified": True}).where(cond)
    sql, params = query.build()
    assert params == (True, 18, "US")


def test_update_without_values():
    """UPDATE without values should raise error"""
    with pytest.raises(ValueError, match="No values to update"):
        Q.update("users").where("id", 1).build()


def test_update_without_table():
    """UPDATE without table should raise error"""
    from sqlo.query.update import UpdateQuery

    query = UpdateQuery("")
    query._table = None
    with pytest.raises(ValueError, match="No table specified"):
        query.build()
