from sqlo import Q


def test_like_operator():
    q = Q.select().from_("users").where("name LIKE", "%john%")
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `name` LIKE %s"
    assert params == ("%john%",)
