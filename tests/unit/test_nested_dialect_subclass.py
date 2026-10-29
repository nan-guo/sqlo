from sqlo import MySQLDialect, Q


class MyMySQL(MySQLDialect):
    pass


def test_a_dialect_subclass_can_nest_queries_of_its_parent():
    sub = Q.select("id").from_("u")
    sql, _ = Q.using(MyMySQL()).select("*").from_("t").where_in("id", sub).build()
    assert sql == "SELECT * FROM `t` WHERE `id` IN (SELECT `id` FROM `u`)"
    inner = Q.using(MyMySQL()).select("id").from_("u")
    sql, _ = Q.select("*").from_("t").where_in("id", inner).build()
    assert "IN (SELECT" in sql
