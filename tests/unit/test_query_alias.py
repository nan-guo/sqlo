import pytest

from sqlo import Q


# --- as_() names the query, it does not alias its own FROM -------------------


def test_as_does_not_add_an_alias_to_the_inner_from():
    sub = Q.select("id").from_("users").as_("active")
    assert sub.build()[0] == "SELECT `id` FROM `users`"


def test_subquery_in_from_gets_the_as_alias_only_outside():
    sub = Q.select("id").from_("users").where("x", 1).as_("active")
    sql, params = Q.select("*").from_(sub).build()
    assert sql == (
        "SELECT * FROM (SELECT `id` FROM `users` WHERE `x` = %s) AS active"
    )
    assert params == (1,)


def test_subquery_in_join_gets_the_as_alias_only_outside():
    sub = Q.select("uid").from_("orders").as_("lo")
    sql, _ = Q.select("*").from_("u").join(sub, "lo.uid = u.id").build()
    assert sql == (
        "SELECT * FROM `u` INNER JOIN (SELECT `uid` FROM `orders`) AS lo "
        "ON lo.uid = u.id"
    )


def test_cte_defaults_to_the_query_alias_without_aliasing_its_from():
    cte = Q.select("id").from_("users").where("x", 1).as_("c")
    sql, _ = Q.select("*").from_("c").with_(cte).build()
    assert sql == (
        "WITH `c` AS (SELECT `id` FROM `users` WHERE `x` = %s) SELECT * FROM `c`"
    )


def test_inner_query_can_use_the_real_table_name_in_qualified_columns():
    """With the old `FROM users s` the name `users.id` stopped being valid in MySQL."""
    sub = Q.select("users.id").from_("users").where("users.active", True).as_("s")
    sql, _ = Q.select("*").from_(sub).build()
    assert sql == (
        "SELECT * FROM (SELECT `users`.`id` FROM `users` "
        "WHERE `users`.`active` = %s) AS s"
    )


# --- the two aliases are independent ----------------------------------------


def test_a_query_can_have_a_table_alias_and_a_query_alias():
    sub = Q.select("x.id").from_("users", "x").where("x.active", True).as_("sub")
    assert sub.build()[0] == (
        "SELECT `x`.`id` FROM `users` x WHERE `x`.`active` = %s"
    )
    sql, _ = Q.select("*").from_(sub).build()
    assert sql == (
        "SELECT * FROM (SELECT `x`.`id` FROM `users` x "
        "WHERE `x`.`active` = %s) AS sub"
    )


def test_order_of_from_and_as_does_not_matter():
    a = Q.select("a").from_("t", "x").as_("q")
    b = Q.select("a").as_("q").from_("t", "x")
    assert a.build() == b.build() == ("SELECT `a` FROM `t` x", ())
    assert a._alias == b._alias == "q"
    assert a._table_alias == b._table_alias == "x"


def test_from_with_a_table_alias_is_unchanged():
    assert Q.select("*").from_("users", "u").build()[0] == "SELECT * FROM `users` u"
    assert (
        Q.select("*").from_("users", alias="u").build()[0] == "SELECT * FROM `users` u"
    )


# --- from_(subquery) -------------------------------------------------------


def test_explicit_alias_overrides_the_subquery_alias():
    sub = Q.select("id").from_("users").as_("a")
    sql, _ = Q.select("*").from_(sub, alias="b").build()
    assert sql == "SELECT * FROM (SELECT `id` FROM `users`) AS b"


def test_from_subquery_does_not_copy_its_alias_onto_the_outer_query():
    sub = Q.select("id").from_("users").as_("s")
    outer = Q.select("*").from_(sub)
    assert outer._alias is None
    assert outer.build()[0] == "SELECT * FROM (SELECT `id` FROM `users`) AS s"
    # so the outer query is not mistaken for something called `s` when embedded
    with pytest.raises(ValueError, match="alias"):
        Q.select("*").from_("t").join(outer, "a = b")


def test_alias_given_to_from_is_validated():
    with pytest.raises(ValueError):
        Q.select("*").from_("users", "a; DROP TABLE x")
    with pytest.raises(ValueError):
        Q.select("*").from_(Q.select("id").from_("t"), "a b")


def test_as_alias_is_validated():
    with pytest.raises(ValueError):
        Q.select("*").from_("users").as_("a; DROP TABLE x")


def test_building_twice_gives_the_same_sql():
    sub = Q.select("id").from_("users", "x").as_("s")
    q = Q.select("*").from_(sub)
    assert q.build() == q.build()


def test_clone_keeps_both_aliases_independent():
    original = Q.select("a").from_("t", "x").as_("q")
    clone = original.clone()
    clone.as_("other")
    assert (original._alias, original._table_alias) == ("q", "x")
    assert (clone._alias, clone._table_alias) == ("other", "x")


def test_union_operand_alias_is_not_added_to_its_from():
    operand = Q.select("a").from_("w").as_("o")
    sql, _ = Q.select("a").from_("t").union(operand).build()
    assert sql == "SELECT `a` FROM `t` UNION SELECT `a` FROM `w`"
