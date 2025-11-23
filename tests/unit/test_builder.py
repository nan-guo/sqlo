"""
Tests for Q builder factory.

Coverage:
- Q.select()
- Q.insert_into()
- Q.update()
- Q.delete_from()
- Query.__str__() for debugging
"""

from sqlo import Q


def test_builder_select():
    """Q.select() creates SelectQuery"""
    query = Q.select("*")
    assert query is not None


def test_builder_insert_into():
    """Q.insert_into() creates InsertQuery"""
    query = Q.insert_into("users")
    assert query is not None


def test_builder_update():
    """Q.update() creates UpdateQuery"""
    query = Q.update("users")
    assert query is not None


def test_builder_delete_from():
    """Q.delete_from() creates DeleteQuery"""
    query = Q.delete_from("users")
    assert query is not None


def test_query_str_method():
    """Query.__str__() for debugging"""
    query = Q.select("*").from_("users").where("id", 1)
    sql_str = str(query)
    assert "SELECT * FROM `users` WHERE `id` = ?" in sql_str
