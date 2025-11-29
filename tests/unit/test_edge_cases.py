"""Edge case handling tests.

This test suite verifies that sqlo correctly handles various edge cases
like empty lists, NULL values, and unsafe operations.
"""

import pytest

from sqlo import Q


class TestEmptyListHandling:
    """Test handling of empty lists in WHERE IN clauses."""

    def test_where_in_empty_list(self):
        """WHERE IN ([]) should generate WHERE FALSE."""
        sql, params = Q.select("*").from_("users").where_in("id", []).build()
        assert "FALSE" in sql
        assert len(params) == 0

    def test_where_not_in_empty_list(self):
        """WHERE NOT IN ([]) should generate WHERE TRUE."""
        sql, params = Q.select("*").from_("users").where_not_in("id", []).build()
        assert "TRUE" in sql
        assert len(params) == 0

    def test_or_where_in_empty_list(self):
        """OR WHERE IN ([]) should generate OR FALSE."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where("active", True)
            .or_where_in("id", [])
            .build()
        )
        assert "FALSE" in sql
        assert "active" in sql

    def test_or_where_not_in_empty_list(self):
        """OR WHERE NOT IN ([]) should generate OR TRUE."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where("active", False)
            .or_where_not_in("id", [])
            .build()
        )
        assert "TRUE" in sql


class TestNullValueHandling:
    """Test handling of NULL values across different query types."""

    def test_insert_with_null(self):
        """INSERT should handle NULL values correctly."""
        sql, params = (
            Q.insert_into("users").values({"name": "Alice", "email": None}).build()
        )
        assert "name" in sql
        assert "email" in sql
        assert None in params

    def test_update_with_null(self):
        """UPDATE should handle NULL values correctly."""
        sql, params = (
            Q.update("users")
            .set({"email": None})
            .where("id", 1)
            .allow_all_rows()  # Skip WHERE check for this test
            .build()
        )
        # Remove allow_all_rows call after WHERE is added
        sql, params = Q.update("users").set({"email": None}).where("id", 1).build()
        assert None in params

    def test_where_null_condition(self):
        """WHERE NULL should use IS NULL operator."""
        sql, params = Q.select("*").from_("users").where_null("deleted_at").build()
        assert "IS NULL" in sql
        assert "deleted_at" in sql

    def test_where_not_null_condition(self):
        """WHERE NOT NULL should use IS NOT NULL operator."""
        sql, params = Q.select("*").from_("users").where_not_null("email").build()
        assert "IS NOT NULL" in sql
        assert "email" in sql

    def test_multiple_null_values_in_insert(self):
        """Test batch insert with some NULL values."""
        sql, params = (
            Q.insert_into("users")
            .values(
                [
                    {"name": "Alice", "email": "alice@example.com"},
                    {"name": "Bob", "email": None},
                ]
            )
            .build()
        )
        assert params.count(None) == 1  # One NULL email


class TestUpdateDeleteSafety:
    """Test safety checks for UPDATE and DELETE without WHERE."""

    def test_update_without_where_raises(self):
        """UPDATE without WHERE should raise ValueError."""
        with pytest.raises(ValueError, match="UPDATE without WHERE clause"):
            Q.update("users").set({"active": False}).build()

    def test_update_with_allow_all_rows(self):
        """UPDATE with allow_all_rows() should work."""
        sql, params = Q.update("users").set({"active": False}).allow_all_rows().build()
        assert "UPDATE" in sql
        assert "active" in sql
        assert len(params) == 1

    def test_update_with_where_works(self):
        """UPDATE with WHERE should work normally."""
        sql, params = Q.update("users").set({"active": False}).where("id", 1).build()
        assert "WHERE" in sql

    def test_delete_without_where_raises(self):
        """DELETE without WHERE should raise ValueError."""
        with pytest.raises(ValueError, match="DELETE without WHERE clause"):
            Q.delete_from("users").build()

    def test_delete_with_allow_all_rows(self):
        """DELETE with allow_all_rows() should work."""
        sql, params = Q.delete_from("temp_table").allow_all_rows().build()
        assert "DELETE FROM" in sql

    def test_delete_with_where_works(self):
        """DELETE with WHERE should work normally."""
        sql, params = Q.delete_from("users").where("id", 1).build()
        assert "WHERE" in sql


class TestBoundaryConditions:
    """Test boundary conditions and special cases."""

    def test_single_item_in_list(self):
        """WHERE IN with single item should work."""
        sql, params = Q.select("*").from_("users").where_in("id", [1]).build()
        assert "IN" in sql
        assert params == (1,)

    def test_large_in_list(self):
        """WHERE IN with large list should work."""
        large_list = list(range(1000))
        sql, params = Q.select("*").from_("users").where_in("id", large_list).build()
        assert "IN" in sql
        assert len(params) == 1000

    def test_update_limit_without_order_by(self):
        """UPDATE with LIMIT but no ORDER BY should work."""
        sql, params = (
            Q.update("users")
            .set({"active": False})
            .where("active", True)
            .limit(10)
            .build()
        )
        assert "LIMIT 10" in sql

    def test_delete_limit_without_order_by(self):
        """DELETE with LIMIT but no ORDER BY should work."""
        sql, params = Q.delete_from("users").where("active", False).limit(10).build()
        assert "LIMIT 10" in sql

    def test_empty_values_dict_in_update(self):
        """UPDATE with empty values dict should raise."""
        with pytest.raises(ValueError, match="No values to update"):
            Q.update("users").where("id", 1).build()

    def test_empty_values_list_in_insert(self):
        """INSERT with empty values should raise."""
        with pytest.raises(ValueError, match="No values to insert"):
            Q.insert_into("users").build()


class TestWhereInUpdate:
    """Test WHERE IN in UPDATE queries with empty lists."""

    def test_update_where_in_empty(self):
        """UPDATE with WHERE IN empty list."""
        sql, params = (
            Q.update("users").set({"active": False}).where_in("id", []).build()
        )
        # Since WHERE IN ([]) → FALSE, this is safe (updates nothing)
        assert "FALSE" in sql


class TestWhereInDelete:
    """Test WHERE IN in DELETE queries with empty lists."""

    def test_delete_where_in_empty(self):
        """DELETE with WHERE IN empty list."""
        sql, params = Q.delete_from("users").where_in("id", []).build()
        # Since WHERE IN ([]) → FALSE, this is safe (deletes nothing)
        assert "FALSE" in sql


class TestMultipleEmptyConditions:
    """Test combinations of empty list conditions."""

    def test_multiple_empty_in_conditions(self):
        """Multiple WHERE IN empty lists."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where_in("id", [])
            .where_in("status", [])
            .build()
        )
        # Should have multiple FALSE conditions
        assert sql.count("FALSE") == 2

    def test_empty_in_with_regular_where(self):
        """Empty WHERE IN combined with regular WHERE."""
        sql, params = (
            Q.select("*")
            .from_("users")
            .where("active", True)
            .where_in("id", [])
            .build()
        )
        assert "active" in sql
        assert "FALSE" in sql
        assert params == (True,)
