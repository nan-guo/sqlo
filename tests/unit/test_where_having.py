import pytest

from sqlo import Condition, Q


def test_where_simple():
    """Simple WHERE clause"""
    query = Q.select("*").from_("users").where("age", 25)
    sql, params = query.build()
    assert "WHERE `age` = %s" in sql
    assert params == (25,)


def test_where_with_operator():
    """WHERE with custom operator"""
    query = Q.select("*").from_("products").where("price", 100, operator=">=")
    sql, params = query.build()
    assert "`price` >= %s" in sql
    assert params == (100,)


def test_where_with_space_in_column():
    """WHERE with operator in column name (e.g., 'age >')"""
    query = Q.select("*").from_("users").where("age >=", 21)
    sql, params = query.build()
    assert "`age` >= %s" in sql
    assert params == (21,)


def test_having_simple():
    """Simple HAVING clause"""
    query = Q.select("age").from_("users").group_by("age").having("age >", 18)
    sql, params = query.build()
    assert "HAVING `age` > %s" in sql
    assert params == (18,)


def test_having_with_operator():
    """HAVING with custom operator"""
    query = (
        Q.select("category")
        .from_("products")
        .group_by("category")
        .having("category", "Electronics", operator="!=")
    )
    sql, params = query.build()
    assert "HAVING `category` != %s" in sql
    assert params == ("Electronics",)


def test_having_with_condition():
    """HAVING with Condition object"""
    cond = Condition("category", "Electronics")
    query = Q.select("category").from_("products").group_by("category").having(cond)
    sql, params = query.build()
    assert "HAVING (`category` = %s)" in sql
    assert params == ("Electronics",)


def test_invalid_where_clause():
    """Invalid WHERE clause (missing value) raises error"""
    with pytest.raises(ValueError, match="Invalid where clause"):
        Q.select("*").from_("users").where("column")


def test_invalid_having_clause():
    """Invalid HAVING clause (missing value) raises error"""
    with pytest.raises(ValueError, match="Invalid where clause"):  # Uses same mixin
        Q.select("*").from_("users").having("column")
