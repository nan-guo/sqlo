from sqlo import Condition, Q


def test_compact_condition_in_where():
    q = Q.select().from_("users").where("age>", 18)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `age` > %s"
    assert params == (18,)


def test_compact_condition_in_where_gte():
    q = Q.select().from_("users").where("age>=", 18)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `age` >= %s"
    assert params == (18,)


def test_compact_condition_in_where_neq():
    q = Q.select().from_("users").where("age!=", 18)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `age` != %s"
    assert params == (18,)


def test_compact_condition_object():
    c = Condition("age>", 18)
    sql, params = c.build()
    assert sql == "`age` > %s"
    assert params == (18,)


def test_compact_condition_object_gte():
    c = Condition("age>=", 18)
    sql, params = c.build()
    assert sql == "`age` >= %s"
    assert params == (18,)


def test_spaced_condition_still_works():
    q = Q.select().from_("users").where("age >", 18)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `age` > %s"
    assert params == (18,)


def test_dot_notation_compact():
    q = Q.select().from_("users").where("table.age>", 18)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `table`.`age` > %s"
    assert params == (18,)
