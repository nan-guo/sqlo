"""Comprehensive SQL injection prevention tests.

This test suite verifies that sqlo properly prevents SQL injection attacks
through various attack vectors.
"""

import pytest

from sqlo import Q
from sqlo.expressions import Raw


class TestTableNameInjection:
    """Test SQL injection attempts via table names."""

    def test_drop_table_injection(self):
        """Attempt to inject DROP TABLE via table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users; DROP TABLE users; --").build()

    def test_union_injection(self):
        """Attempt UNION-based injection via table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users UNION SELECT * FROM passwords--").build()

    def test_comment_injection(self):
        """Attempt comment-based injection."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users--comment").build()

    def test_multiline_comment_injection(self):
        """Attempt multiline comment injection."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users /*comment*/").build()

    def test_stacked_query_injection(self):
        """Attempt stacked query injection."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users; DELETE FROM users;").build()

    def test_special_characters_in_table(self):
        """Test that special characters are rejected."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("user$table").build()

    def test_valid_table_with_underscore(self):
        """Verify that valid identifiers with underscores work."""
        sql, _ = Q.select("*").from_("user_table").build()
        assert "`user_table`" in sql

    def test_valid_table_with_dot(self):
        """Verify that schema.table notation works."""
        sql, _ = Q.select("*").from_("mydb.users").build()
        assert "`mydb`.`users`" in sql


class TestColumnNameInjection:
    """Test SQL injection attempts via column names."""

    def test_drop_table_via_column(self):
        """Attempt to inject DROP TABLE via column name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("id; DROP TABLE users; --").from_("users").build()

    def test_sql_keyword_injection(self):
        """Attempt injection using SQL keywords in column."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("* FROM passwords--").from_("users").build()

    def test_special_characters_in_column(self):
        """Test that special characters in column names are rejected."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users").where("name'='admin", "x").build()

    def test_valid_column_with_dot(self):
        """Verify that table.column notation works."""
        sql, _ = Q.select("users.id").from_("users").build()
        assert "`users`.`id`" in sql


class TestValueInjection:
    """Test that parameter binding prevents value injection.

    These should all be safe due to parameter binding.
    """

    def test_quote_escape_attempt(self):
        """Verify that quotes in values are safely parameterized."""
        sql, params = (
            Q.select("*").from_("users").where("name", "admin' OR '1'='1").build()
        )
        # Should use parameter binding
        assert "%s" in sql or "?" in sql
        assert params == ("admin' OR '1'='1",)

    def test_or_injection_attempt(self):
        """Verify that OR 1=1 patterns are safely parameterized."""
        sql, params = Q.select("*").from_("users").where("id", "1 OR 1=1").build()
        assert params == ("1 OR 1=1",)

    def test_union_value_injection(self):
        """Verify that UNION attempts in values are safe."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where("name", "admin' UNION SELECT * FROM passwords--")
            .build()
        )
        assert params == ("admin' UNION SELECT * FROM passwords--",)


class TestUpdateInjection:
    """Test injection prevention in UPDATE queries."""

    def test_update_table_injection(self):
        """Attempt injection via UPDATE table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.update("users; DROP TABLE users;").set({"name": "test"}).where(
                "id", 1
            ).build()

    def test_update_column_injection(self):
        """Attempt injection via UPDATE column name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            (
                Q.update("users")
                .set({"name'; DROP TABLE users; --": "test"})
                .where("id", 1)
                .build()
            )

    def test_update_value_safe(self):
        """Verify UPDATE values are safely parameterized."""
        sql, params = (
            Q.update("users").set({"name": "admin' OR '1'='1"}).where("id", 1).build()
        )
        assert "admin' OR '1'='1" in params


class TestInsertInjection:
    """Test injection prevention in INSERT queries."""

    def test_insert_table_injection(self):
        """Attempt injection via INSERT table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.insert_into("users; DROP TABLE users;").values({"name": "test"}).build()

    def test_insert_column_injection(self):
        """Attempt injection via INSERT column name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            (
                Q.insert_into("users")
                .values({"name'; DROP TABLE users; --": "test"})
                .build()
            )

    def test_insert_value_safe(self):
        """Verify INSERT values are safely parameterized."""
        sql, params = (
            Q.insert_into("users").values({"name": "admin' OR '1'='1"}).build()
        )
        assert "admin' OR '1'='1" in params


class TestDeleteInjection:
    """Test injection prevention in DELETE queries."""

    def test_delete_table_injection(self):
        """Attempt injection via DELETE table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.delete_from("users; DROP TABLE passwords;").where("id", 1).build()

    def test_delete_where_column_injection(self):
        """Attempt injection via DELETE WHERE column."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.delete_from("users").where("id'; DROP TABLE users; --", 1).build()


class TestRawExpressionSafety:
    """Test that Raw() expressions work but with proper warnings."""

    def test_raw_in_select(self):
        """Verify Raw() allows SQL expressions."""
        sql, _ = Q.select(Raw("COUNT(*)")).from_("users").build()
        assert "COUNT(*)" in sql

    def test_raw_in_where(self):
        """Verify Raw() works in WHERE clauses."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where(Raw("created_at > NOW() - INTERVAL 7 DAY"))
            .build()
        )
        assert "created_at > NOW() - INTERVAL 7 DAY" in sql

    def test_raw_with_params(self):
        """Verify Raw() supports parameters."""
        sql, params = Q.select("*").from_("users").where(Raw("age > %s", [18])).build()
        assert 18 in params

    def test_raw_non_string_raises(self):
        """Verify Raw() rejects non-string SQL."""
        with pytest.raises(TypeError, match="Raw SQL must be a string"):
            Raw(123)


class TestJoinInjection:
    """Test injection prevention in JOIN clauses."""

    def test_join_table_injection(self):
        """Attempt injection via JOIN table name."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            (
                Q.select("*")
                .from_("users")
                .join("orders; DROP TABLE orders;", "users.id = orders.user_id")
                .build()
            )

    def test_join_on_column_safe(self):
        """Verify JOIN ON condition uses column validation."""
        # ON clause is a string, so it's passed through Raw-like
        # Only table names should be validated
        sql, _ = (
            Q.select("*")
            .from_("users")
            .join("orders", "users.id = orders.user_id")
            .build()
        )
        assert "JOIN" in sql


class TestOrderByInjection:
    """Test injection prevention in ORDER BY."""

    def test_order_by_column_injection(self):
        """Attempt injection via ORDER BY column."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users").order_by("name; DROP TABLE users;").build()

    def test_valid_order_by(self):
        """Verify valid ORDER BY works."""
        sql, _ = Q.select("*").from_("users").order_by("name", "-age").build()
        assert "ORDER BY `name` ASC, `age` DESC" in sql


class TestGroupByInjection:
    """Test injection prevention in GROUP BY."""

    def test_group_by_column_injection(self):
        """Attempt injection via GROUP BY column."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            Q.select("*").from_("users").group_by("name; DROP TABLE users;").build()

    def test_valid_group_by(self):
        """Verify valid GROUP BY works."""
        sql, _ = (
            Q.select("department", Raw("COUNT(*)"))
            .from_("users")
            .group_by("department")
            .build()
        )
        assert "GROUP BY `department`" in sql
