from sqlo import Q
from sqlo.dialects.mysql import MySQLDialect


def test_builder_select():
    query = Q.select("*")
    assert query is not None


def test_builder_insert_into():
    query = Q.insert_into("users")
    assert query is not None


def test_builder_update():
    query = Q.update("users")
    assert query is not None


def test_builder_delete_from():
    query = Q.delete_from("users")
    assert query is not None


def test_query_str_method():
    query = Q.select("*").from_("users").where("id", 1)
    sql_str = str(query)
    assert "SELECT * FROM `users` WHERE `id` = %s" in sql_str


def test_default_dialect_is_mysql():
    """Q should use MySQL dialect by default"""
    dialect = Q.get_dialect()
    assert isinstance(dialect, MySQLDialect)


def test_set_dialect():
    """Q.set_dialect() should change the default dialect"""
    # Save original
    original_dialect = Q.get_dialect()

    # Create custom dialect
    custom_dialect = MySQLDialect()
    Q.set_dialect(custom_dialect)

    assert Q.get_dialect() is custom_dialect

    # Restore original
    Q.set_dialect(original_dialect)


def test_queries_use_default_dialect():
    """Queries created via Q should use the default dialect"""
    query = Q.select("*").from_("users").where("id", 1)
    sql, params = query.build()
    # MySQL uses %s placeholder
    assert "WHERE `id` = %s" in sql
    assert params == (1,)
