import pytest

from sqlo import Q, Raw


def test_insert_single_row():
    """INSERT single row"""
    query = Q.insert_into("users").values([{"name": "Alice", "age": 25}])
    sql, params = query.build()
    assert sql == "INSERT INTO `users` (`name`, `age`) VALUES (%s, %s)"
    assert params == ("Alice", 25)


def test_insert_batch():
    """INSERT multiple rows (batch insert)"""
    q = Q.insert_into("users").values(
        [{"name": "A", "age": 20}, {"name": "B", "age": 30}]
    )
    sql, params = q.build()
    assert sql == "INSERT INTO `users` (`name`, `age`) VALUES (%s, %s), (%s, %s)"
    assert params == ("A", 20, "B", 30)


def test_insert_ignore():
    """INSERT IGNORE"""
    query = (
        Q.insert_into("users")
        .values([{"name": "John", "email": "john@example.com"}])
        .ignore()
    )
    sql, params = query.build()
    assert sql == "INSERT IGNORE INTO `users` (`name`, `email`) VALUES (%s, %s)"
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
    assert "`count` = %s" in sql
    assert params == ("test@example.com", 1, 5)


def test_insert_without_values():
    """INSERT without values should raise error"""
    with pytest.raises(ValueError, match="No values to insert"):
        Q.insert_into("users").build()


def test_insert_values_dict():
    """INSERT with single dict values (not list)"""
    query = Q.insert_into("users").values({"name": "Alice"})
    sql, params = query.build()
    assert sql == "INSERT INTO `users` (`name`) VALUES (%s)"
    assert params == ("Alice",)


def test_insert_from_select():
    """INSERT ... SELECT"""
    select_query = Q.select("name", "email").from_("old_users").where("active", True)
    query = Q.insert_into("users").from_select(["name", "email"], select_query)

    sql, params = query.build()
    assert sql.startswith("INSERT INTO `users` (`name`, `email`) SELECT")
    assert "FROM `old_users`" in sql
    assert "WHERE `active` = %s" in sql
    assert params == (True,)


def test_insert_from_select_no_columns():
    """INSERT ... SELECT without columns should raise error"""
    select_query = Q.select("*").from_("old_users")
    query = Q.insert_into("users")
    # Manually set private attr to simulate invalid state if from_select didn't enforce it
    # But from_select signature requires columns, so we test the build validation
    query._from_select = select_query
    query._select_columns = None

    with pytest.raises(ValueError, match="Columns must be specified"):
        query.build()


def test_insert_on_duplicate_complex():
    """INSERT ... ON DUPLICATE KEY UPDATE with complex expressions"""
    query = (
        Q.insert_into("stats")
        .values({"id": 1, "count": 1})
        .on_duplicate_key_update(
            {
                "count": "count + 1",
                "updated_at": Raw("NOW()"),
                "name": "VALUES(name)",
                "status": "active",
            }
        )
    )
    sql, params = query.build()
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "`count` = count + 1" in sql
    assert "`updated_at` = NOW()" in sql
    assert "`name` = VALUES(name)" in sql
    assert "`status` = %s" in sql
    assert params[-1] == "active"
