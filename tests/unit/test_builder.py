from sqlo import Q


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
