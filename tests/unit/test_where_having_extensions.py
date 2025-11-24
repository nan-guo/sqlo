import pytest
from sqlo import Q

def test_or_where_in():
    """OR WHERE IN clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_in("status", ["active", "pending"])
    sql, params = query.build()
    assert "WHERE `age` = %s OR `status` IN (%s, %s)" in sql
    assert params == (25, "active", "pending")


def test_or_where_not_in():
    """OR WHERE NOT IN clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_not_in("status", ["banned", "deleted"])
    sql, params = query.build()
    assert "WHERE `age` = %s OR `status` NOT IN (%s, %s)" in sql
    assert params == (25, "banned", "deleted")


def test_or_where_null():
    """OR WHERE IS NULL clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_null("deleted_at")
    sql, params = query.build()
    assert "WHERE `age` = %s OR `deleted_at` IS NULL" in sql
    assert params == (25,)


def test_or_where_not_null():
    """OR WHERE IS NOT NULL clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_not_null("email")
    sql, params = query.build()
    assert "WHERE `age` = %s OR `email` IS NOT NULL" in sql
    assert params == (25,)


def test_or_where_between():
    """OR WHERE BETWEEN clause"""
    query = Q.select("*").from_("users").where("status", "active").or_where_between("age", 18, 65)
    sql, params = query.build()
    assert "WHERE `status` = %s OR `age` BETWEEN %s AND %s" in sql
    assert params == ("active", 18, 65)


def test_or_where_not_between():
    """OR WHERE NOT BETWEEN clause"""
    query = Q.select("*").from_("users").where("status", "active").or_where_not_between("age", 18, 65)
    sql, params = query.build()
    assert "WHERE `status` = %s OR `age` NOT BETWEEN %s AND %s" in sql
    assert params == ("active", 18, 65)


def test_or_where_like():
    """OR WHERE LIKE clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_like("name", "John%")
    sql, params = query.build()
    assert "WHERE `age` = %s OR `name` LIKE %s" in sql
    assert params == (25, "John%")


def test_or_where_not_like():
    """OR WHERE NOT LIKE clause"""
    query = Q.select("*").from_("users").where("age", 25).or_where_not_like("name", "John%")
    sql, params = query.build()
    assert "WHERE `age` = %s OR `name` NOT LIKE %s" in sql
    assert params == (25, "John%")
