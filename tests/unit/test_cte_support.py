"""Tests for CTE (Common Table Expression) support."""

from sqlo import Q, func


def test_cte_basic():
    """Test basic CTE functionality."""
    # Create a CTE
    cte = (
        Q.select("user_id", func.count("*").as_("order_count"))
        .from_("orders")
        .group_by("user_id")
        .as_("user_orders")
    )

    # Use CTE in main query
    q = (
        Q.select("u.name", "uo.order_count")
        .with_(cte)
        .from_("users", alias="u")
        .join("user_orders uo", "u.id = uo.user_id")
    )

    sql, _ = q.build()

    # Verify CTE structure
    assert "WITH `user_orders` AS" in sql
    assert "SELECT `user_id`, COUNT(*) AS `order_count`" in sql
    assert "FROM `orders`" in sql
    assert "GROUP BY `user_id`" in sql

    # Verify main query
    assert "SELECT `u`.`name`, `uo`.`order_count`" in sql
    assert "FROM `users` u" in sql


def test_cte_multiple():
    """Test multiple CTEs."""
    cte1 = Q.select("user_id").from_("orders").as_("order_users")
    cte2 = Q.select("user_id").from_("payments").as_("payment_users")

    q = Q.select("*").with_(cte1).with_(cte2).from_("users")

    sql, _ = q.build()

    assert "WITH `order_users` AS" in sql
    assert "`payment_users` AS" in sql


def test_cte_recursive():
    """Test recursive CTE."""
    cte = Q.select("id", "parent_id").from_("categories").as_("cat_tree")

    q = Q.select("*").with_(cte, recursive=True).from_("cat_tree")
    sql, _ = q.build()

    assert "WITH RECURSIVE" in sql


def test_cte_with_insert():
    """Test CTE with INSERT query."""
    cte = Q.select("id").from_("active_users").as_("active")

    q = Q.insert_into("user_logs").with_(cte).values({"user_id": 1, "action": "login"})

    sql, _ = q.build()

    assert "WITH `active` AS" in sql
    assert "INSERT INTO `user_logs`" in sql


def test_cte_with_update():
    """Test CTE with UPDATE query."""
    cte = Q.select("id").from_("premium_users").as_("premium")

    q = (
        Q.update("users")
        .with_(cte)
        .set({"status": "premium"})
        .where_in("id", Q.select("id").from_("premium"))
    )

    sql, _ = q.build()

    assert "WITH `premium` AS" in sql
    assert "UPDATE `users`" in sql


def test_cte_with_delete():
    """Test CTE with DELETE query."""
    cte = Q.select("id").from_("inactive_users").as_("inactive")

    q = (
        Q.delete_from("users")
        .with_(cte)
        .where_in("id", Q.select("id").from_("inactive"))
    )

    sql, _ = q.build()

    assert "WITH `inactive` AS" in sql
    assert "DELETE FROM `users`" in sql


def test_cte_without_name_raises_error():
    """Test that CTE without name raises ValueError."""
    import pytest

    cte = Q.select("id").from_("users")  # No .as_() call

    q = Q.select("*").from_("data")

    with pytest.raises(ValueError, match="CTE name must be provided"):
        q.with_(cte)


def test_cte_with_string_query():
    """Test CTE with string query (non-build object)."""
    # This tests the else branch in _build_ctes when query doesn't have build()
    q = Q.select("*").from_("users")
    # Manually add a string CTE (simulating edge case)
    q._ctes.append(("SELECT 1", "dummy", False))

    sql, _ = q.build()

    assert "WITH `dummy` AS (SELECT 1)" in sql


def test_debug_method():
    """Test debug() method prints SQL and returns self."""
    import io
    import sys

    q = Q.select("name").from_("users").where("id", 1)

    # Capture stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output

    result = q.debug()

    # Restore stdout
    sys.stdout = sys.__stdout__

    output = captured_output.getvalue()

    # Verify debug output was printed
    assert "[sqlo DEBUG]" in output
    assert "SELECT" in output
    assert "Params:" in output

    # Verify it returns self for chaining
    assert result is q
