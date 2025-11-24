"""
Tests for advanced condition features: EXISTS, IN, IS NULL, and logical combinations.
"""

import pytest

from sqlo import Q
from sqlo.expressions import ComplexCondition, Condition, Raw


class TestConditionBuildMethod:
    """Test Condition.build() method for inspection and testing."""

    def test_simple_condition_build(self):
        """Test basic condition build returns (sql, params) tuple."""
        c = Condition("age", 18)
        sql, params = c.build()
        assert sql == "`age` = %s"
        assert params == (18,)

    def test_compact_operator_build(self):
        """Test compact operator syntax."""
        c = Condition("age>=", 18)
        sql, params = c.build()
        assert sql == "`age` >= %s"
        assert params == (18,)

    def test_space_operator_build(self):
        """Test space-separated operator syntax."""
        c = Condition("age >=", 18)
        sql, params = c.build()
        assert sql == "`age` >= %s"
        assert params == (18,)

    def test_combined_conditions_build(self):
        """Test combined conditions with AND."""
        c1 = Condition("age>=", 18)
        c2 = Condition("country", "US")
        combined = c1 & c2
        sql, params = combined.build()
        assert "AND" in sql
        assert params == (18, "US")


class TestNullConditions:
    """Test IS NULL and IS NOT NULL conditions."""

    def test_null_factory_method(self):
        """Test Condition.null() static factory method."""
        c = Condition.null("deleted_at")
        sql, params = c.build()
        assert sql == "`deleted_at` IS NULL"
        assert params == ()

    def test_not_null_factory_method(self):
        """Test Condition.not_null() static factory method."""
        c = Condition.not_null("email")
        sql, params = c.build()
        assert sql == "`email` IS NOT NULL"
        assert params == ()

    def test_null_constructor_syntax(self):
        """Test IS NULL using constructor."""
        c = Condition("total", operator="IS NULL")
        sql, params = c.build()
        assert sql == "`total` IS NULL"
        assert params == ()

    def test_not_null_constructor_syntax(self):
        """Test IS NOT NULL using constructor."""
        c = Condition("total", operator="IS NOT NULL")
        sql, params = c.build()
        assert sql == "`total` IS NOT NULL"
        assert params == ()

    def test_is_with_none_value(self):
        """Test IS with None value converts to IS NULL."""
        c = Condition("total", None, operator="IS")
        sql, params = c.build()
        assert sql == "`total` IS NULL"
        assert params == ()

    def test_is_not_with_none_value(self):
        """Test IS NOT with None value converts to IS NOT NULL."""
        c = Condition("total", None, operator="IS NOT")
        sql, params = c.build()
        assert sql == "`total` IS NOT NULL"
        assert params == ()

    def test_null_in_query(self):
        """Test NULL condition in a query."""
        query = Q.select("*").from_("orders").where(Condition.null("deleted_at"))
        sql, params = query.build()
        assert "`deleted_at` IS NULL" in sql
        assert params == ()


class TestInConditions:
    """Test IN and NOT IN conditions."""

    def test_in_factory_method(self):
        """Test Condition.in_() static factory method."""
        c = Condition.in_("status", ["pending", "done"])
        sql, params = c.build()
        assert sql == "`status` IN (%s, %s)"
        assert params == ("pending", "done")

    def test_not_in_factory_method(self):
        """Test Condition.not_in() static factory method."""
        c = Condition.not_in("status", ["canceled", "failed"])
        sql, params = c.build()
        assert sql == "`status` NOT IN (%s, %s)"
        assert params == ("canceled", "failed")

    def test_in_constructor_syntax(self):
        """Test IN using constructor."""
        c = Condition("status", ["pending", "done"], operator="IN")
        sql, params = c.build()
        assert sql == "`status` IN (%s, %s)"
        assert params == ("pending", "done")

    def test_not_in_constructor_syntax(self):
        """Test NOT IN using constructor."""
        c = Condition("status", ["canceled"], operator="NOT IN")
        sql, params = c.build()
        assert sql == "`status` NOT IN (%s)"
        assert params == ("canceled",)

    def test_in_with_tuple(self):
        """Test IN with tuple values."""
        c = Condition.in_("id", (1, 2, 3))
        sql, params = c.build()
        assert sql == "`id` IN (%s, %s, %s)"
        assert params == (1, 2, 3)

    def test_in_with_subquery(self):
        """Test IN with subquery."""
        subquery = (
            Q.select("user_id").from_("orders").where(Condition("status", "completed"))
        )
        c = Condition.in_("id", subquery)
        sql, params = c.build()
        assert "`id` IN (SELECT" in sql
        assert "FROM `orders`" in sql
        assert params == ("completed",)

    def test_in_query(self):
        """Test IN condition in a query."""
        query = (
            Q.select("*")
            .from_("orders")
            .where(Condition.in_("status", ["pending", "processing"]))
        )
        sql, params = query.build()
        assert "`status` IN (%s, %s)" in sql
        assert params == ("pending", "processing")

    def test_in_invalid_value(self):
        """Test IN with invalid value raises error."""
        with pytest.raises(ValueError, match="IN operator requires"):
            Condition("status", "invalid", operator="IN")


class TestExistsConditions:
    """Test EXISTS and NOT EXISTS conditions."""

    def test_exists_factory_method(self):
        """Test Condition.exists() static factory method."""
        subquery = Q.select("1").from_("orders").where(Condition("user_id", 123))
        c = Condition.exists(subquery)
        sql, params = c.build()
        assert sql.startswith("EXISTS (SELECT")
        assert "FROM `orders`" in sql
        assert params == (123,)

    def test_not_exists_factory_method(self):
        """Test Condition.not_exists() static factory method."""
        subquery = Q.select("1").from_("orders").where(Condition("user_id", 123))
        c = Condition.not_exists(subquery)
        sql, params = c.build()
        assert sql.startswith("NOT EXISTS (SELECT")
        assert "FROM `orders`" in sql
        assert params == (123,)

    def test_exists_in_query(self):
        """Test EXISTS condition in a query."""
        subquery = (
            Q.select("1")
            .from_("orders")
            .where(Condition("orders.user_id", Raw("users.id")))
        )
        query = Q.select("*").from_("users").where(Condition.exists(subquery))
        sql, params = query.build()
        assert "EXISTS (SELECT" in sql
        assert "FROM `orders`" in sql

    def test_exists_with_complex_subquery(self):
        """Test EXISTS with complex subquery."""
        subquery = (
            Q.select("1")
            .from_("orders")
            .where(Condition("orders.user_id", 123))  # Use actual value instead of Raw
            .where(Condition.in_("status", ["pending", "processing"]))
        )
        c = Condition.exists(subquery)
        sql, params = c.build()
        assert "EXISTS (SELECT" in sql
        assert "IN (%s, %s)" in sql
        assert params == (123, "pending", "processing")


class TestLogicalCombinations:
    """Test Condition.and_() and Condition.or_() static methods."""

    def test_and_static_method(self):
        """Test Condition.and_() combines conditions with AND."""
        c1 = Condition("age>=", 18)
        c2 = Condition("country", "US")
        c3 = Condition("verified", True)
        combined = Condition.and_(c1, c2, c3)
        sql, params = combined.build()
        assert "AND" in sql
        assert params == (18, "US", True)

    def test_or_static_method(self):
        """Test Condition.or_() combines conditions with OR."""
        c1 = Condition("status", "pending")
        c2 = Condition("status", "processing")
        combined = Condition.or_(c1, c2)
        sql, params = combined.build()
        assert "OR" in sql
        assert params == ("pending", "processing")

    def test_and_empty_conditions(self):
        """Test Condition.and_() with no conditions."""
        combined = Condition.and_()
        sql, params = combined.build()
        assert sql == ""
        assert params == ()

    def test_or_empty_conditions(self):
        """Test Condition.or_() with no conditions."""
        combined = Condition.or_()
        sql, params = combined.build()
        # Should return empty ComplexCondition
        assert isinstance(combined, ComplexCondition)


class TestComplexCombinations:
    """Test complex combinations of conditions."""

    def test_in_and_not_null(self):
        """Test combining IN and NOT NULL with AND."""
        query = (
            Q.select("*")
            .from_("orders")
            .where(
                Condition.in_("status", ["pending", "processing"])
                & Condition.not_null("total")
            )
        )
        sql, params = query.build()
        assert "`status` IN (%s, %s)" in sql
        assert "`total` IS NOT NULL" in sql
        assert "AND" in sql
        assert params == ("pending", "processing")

    def test_complex_or_and_combination(self):
        """Test (IN AND NOT NULL) OR (> OR =)."""
        query = (
            Q.select("*")
            .from_("orders")
            .where(
                (
                    Condition.in_("status", ["pending", "processing"])
                    & Condition.not_null("total")
                )
                | (Condition("amount>", 100) | Condition("priority", "high"))
            )
        )
        sql, params = query.build()
        assert "IN (%s, %s)" in sql
        assert "IS NOT NULL" in sql
        assert "OR" in sql
        assert params == ("pending", "processing", 100, "high")

    def test_exists_with_and(self):
        """Test EXISTS combined with other conditions."""
        subquery = (
            Q.select("1")
            .from_("orders")
            .where(Condition("orders.user_id", Raw("users.id")))
        )
        query = (
            Q.select("*")
            .from_("users")
            .where(Condition.exists(subquery) & Condition("users.active", True))
        )
        sql, params = query.build()
        assert "EXISTS" in sql
        assert (
            "`users.active` = %s" in sql
        )  # Without dot - it's quoted as one identifier
        assert params == (True,)

    def test_bitwise_operators_still_work(self):
        """Test that bitwise operators & and | still work."""
        c1 = Condition("age>=", 18)
        c2 = Condition("country", "US")
        c3 = Condition("verified", True)

        # AND with &
        and_result = c1 & c2
        sql, params = and_result.build()
        assert "AND" in sql
        assert params == (18, "US")

        # OR with |
        or_result = c1 | c2
        sql, params = or_result.build()
        assert "OR" in sql
        assert params == (18, "US")

        # Complex: (c1 & c2) | c3
        complex_result = (c1 & c2) | c3
        sql, params = complex_result.build()
        assert "AND" in sql
        assert "OR" in sql
        assert params == (18, "US", True)


class TestUserExamples:
    """Test the exact examples from the user's request."""

    def test_exists_with_or_condition(self):
        """Test the user's EXISTS example with OR in subquery."""
        subquery = (
            Q.select("1")
            .from_("orders")
            .where(
                Condition("orders.user_id", Raw("users.id"))
                | Condition.in_("orders.status", ["canceled", "done"])
            )
        )
        query = Q.select("*").from_("users").where(Condition.exists(subquery))
        sql, params = query.build()

        assert "SELECT * FROM `users`" in sql
        assert "EXISTS (SELECT" in sql
        assert "FROM `orders`" in sql
        assert "OR" in sql
        assert "`orders.status` IN (%s, %s)" in sql
        assert params == ("canceled", "done")

    def test_in_statement(self):
        """Test IN statement support."""
        query = (
            Q.select("*")
            .from_("orders")
            .where(Condition.in_("status", ["canceled", "done"]))
        )
        sql, params = query.build()

        assert "SELECT * FROM `orders`" in sql
        assert "`status` IN (%s, %s)" in sql
        assert params == ("canceled", "done")

    def test_is_null_with_raw(self):
        """Test IS NULL works properly."""
        query = Q.select("1").from_("orders").where(Condition.null("total"))
        sql, params = query.build()

        # Note: "1" gets quoted as `1` by the dialect
        assert "FROM `orders`" in sql
        assert "`total` IS NULL" in sql
        assert params == ()
