import pytest

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

    # Unknown operators are rejected
    with pytest.raises(ValueError):
        Q.select().from_("users").where("age MY_OP", 10)


def test_is_operator():
    # IS TRUE
    q = Q.select().from_("users").where("active IS", True)
    sql, params = q.build()
    assert sql == "SELECT * FROM `users` WHERE `active` IS %s"
    assert params == (True,)
