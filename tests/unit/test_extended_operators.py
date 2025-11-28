from sqlo import Q


def test_extended_operators():
    # NOT LIKE
    q = Q.select().from_("users").where("name NOT LIKE", "%john%")
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `name` NOT LIKE %s"
    assert params == ("%john%",)

    # REGEXP
    q = Q.select().from_("users").where("name REGEXP", "^J.*")
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `name` REGEXP %s"
    assert params == ("^J.*",)

    # Custom/Weird Operator (just to prove regex flexibility)
    q = Q.select().from_("users").where("age MY_OP", 10)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `age` MY_OP %s"
    assert params == (10,)


def test_is_operator():
    # IS TRUE
    q = Q.select().from_("users").where("active IS", True)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `active` IS %s"
    assert params == (True,)
