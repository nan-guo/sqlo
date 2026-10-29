import pytest

from sqlo import Q


def _sub():
    return Q.select("id").from_("users").where("active", True)


def test_a_subquery_in_from_without_an_alias_is_rejected():
    with pytest.raises(ValueError, match="alias"):
        Q.select("*").from_(_sub()).build()


def test_the_error_says_how_to_fix_it():
    with pytest.raises(ValueError, match=r"as_\(\).*from_\("):
        Q.select("*").from_(_sub()).build()


def test_an_alias_from_as_is_enough():
    sql, params = Q.select("*").from_(_sub().as_("s")).build()
    assert sql == "SELECT * FROM (SELECT `id` FROM `users` WHERE `active` = %s) AS s"
    assert params == (True,)


def test_an_alias_passed_to_from_is_enough():
    sql, _ = Q.select("*").from_(_sub(), alias="s").build()
    assert sql == "SELECT * FROM (SELECT `id` FROM `users` WHERE `active` = %s) AS s"


def test_the_alias_may_be_given_after_from():
    sub = _sub()
    q = Q.select("*").from_(sub)
    sub.as_("s")
    assert q.build()[0].endswith(") AS s")


def test_the_check_happens_at_build_so_chaining_order_is_free():
    q = Q.select("*").from_(_sub())  # no error yet
    with pytest.raises(ValueError, match="alias"):
        q.build()


def test_other_subquery_positions_do_not_need_an_alias():
    sub = _sub()
    assert "IN (SELECT" in Q.select("*").from_("t").where_in("id", sub).build()[0]
    assert "UNION SELECT" in Q.select("id").from_("t").union(sub).build()[0]
    assert "EXISTS (SELECT" in str(
        Q.select("*").from_("t").where(__import__("sqlo").Condition.exists(sub))
    )


def test_a_string_table_never_needs_an_alias():
    assert Q.select("*").from_("users").build()[0] == "SELECT * FROM `users`"
