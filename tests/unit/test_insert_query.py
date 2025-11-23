"""
Tests for INSERT queries.

Coverage:
- Single row insert
- Batch insert (multiple rows)
- INSERT IGNORE
- ON DUPLICATE KEY UPDATE
- Error handling
"""

import pytest

from sqlo import Q


def test_insert_single_row():
    """INSERT single row"""
    query = Q.insert_into("users").values([{"name": "Alice", "age":25}])
    sql, params = query.build()
    assert sql == "INSERT INTO `users` (`name`, `age`) VALUES (?, ?)"
    assert params == ("Alice", 25)


def test_insert_batch():
    """INSERT multiple rows (batch insert)"""
    q = Q.insert_into("users").values(
        [{"name": "A", "age": 20}, {"name": "B", "age": 30}]
    )
    sql, params = q.build()
    assert sql == "INSERT INTO `users` (`name`, `age`) VALUES (?, ?), (?, ?)"
    assert params == ("A", 20, "B", 30)


def test_insert_ignore():
    """INSERT IGNORE"""
    query = (
        Q.insert_into("users")
        .values([{"name": "John", "email": "john@example.com"}])
        .ignore()
    )
    sql, params = query.build()
    assert sql == "INSERT IGNORE INTO `users` (`name`, `email`) VALUES (?, ?)"
    assert params == ("John", "john@example.com")


def test_insert_on_duplicate_key_update():
    """INSERT ... ON DUPLICATE KEY UPDATE"""
    query = (
        Q.insert_into("users")
        .values([{"email": "test@example.com", "count": 1}])
        .on_duplicate_key_update({"count": 5})
    )
    sql, params = query.build()
    assert "INSERT INTO `users`" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "`count` = ?" in sql
    assert params == ("test@example.com", 1, 5)


def test_insert_without_values():
    """INSERT without values should raise error"""
    with pytest.raises(ValueError, match="No values to insert"):
        Q.insert_into("users").build()
