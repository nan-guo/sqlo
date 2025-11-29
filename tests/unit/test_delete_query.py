import pytest

from sqlo import Condition, Q, Raw


def test_delete_basic():
    """Basic DELETE with WHERE"""
    q = Q.delete_from("users").where("id", 1)
    sql, params = q.build()
    assert sql == "DELETE FROM `users` WHERE `id` = %s"
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


def test_delete_join():
    """DELETE with JOIN (MySQL multi-table delete)"""
    query = (
        Q.delete_from("users")
        .join("orders", "orders.user_id = users.id")
        .where("orders.status", "cancelled")
    )
    sql, params = query.build()
    assert "DELETE FROM `users` INNER JOIN orders ON orders.user_id = users.id" in sql
    assert "WHERE `orders`.`status` = %s" in sql
    assert params == ("cancelled",)


def test_delete_left_join():
    """DELETE with LEFT JOIN"""
    query = (
        Q.delete_from("users")
        .left_join("orders", "orders.user_id = users.id")
        .where_null("orders.id")
    )
    sql, params = query.build()
    assert "DELETE FROM `users` LEFT JOIN orders ON orders.user_id = users.id" in sql
    assert "WHERE `orders`.`id` IS NULL" in sql


def test_delete_order_by_desc():
    """DELETE with ORDER BY DESC"""
    query = Q.delete_from("logs").order_by("-created_at").allow_all_rows()
    sql, _ = query.build()
    assert "ORDER BY `created_at` DESC" in sql


def test_delete_multiple_joins():
    """DELETE with multiple JOINs"""
    query = (
        Q.delete_from("t1")
        .join("t2", "t1.id = t2.t1_id")
        .left_join("t3", "t2.id = t3.t2_id")
        .allow_all_rows()
    )
    sql, _ = query.build()
    assert "INNER JOIN t2" in sql
    assert "LEFT JOIN t3" in sql
