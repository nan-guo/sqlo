import pytest

from sqlo import Condition, Q


def _select():
    return Q.select("*").from_("u")


# --- OFFSET needs LIMIT ------------------------------------------------


def test_offset_without_limit_is_rejected_at_build():
    q = _select().offset(5)
    with pytest.raises(ValueError, match="offset.*limit"):
        q.build()


def test_offset_zero_without_limit_is_fine():
    sql, _ = _select().offset(0).build()
    assert sql == "SELECT * FROM `u`"


def test_limit_and_offset_still_work_in_any_order():
    for q in (_select().limit(10).offset(20), _select().offset(20).limit(10)):
        sql, _ = q.build()
        assert sql == "SELECT * FROM `u` LIMIT 10 OFFSET 20"


def test_paginate_still_works():
    sql, _ = _select().paginate(page=3, per_page=20).build()
    assert sql == "SELECT * FROM `u` LIMIT 20 OFFSET 40"


def test_limit_zero_with_offset_is_accepted():
    sql, _ = _select().limit(0).offset(5).build()
    assert sql == "SELECT * FROM `u` LIMIT 0 OFFSET 5"


def test_offset_without_limit_is_rejected_with_a_union():
    other = Q.select("*").from_("v")
    with pytest.raises(ValueError, match="offset.*limit"):
        _select().union(other).offset(3).build()
    sql, _ = _select().union(other).limit(5).offset(3).build()
    assert sql.endswith("UNION SELECT * FROM `v` LIMIT 5 OFFSET 3")


# --- where / or_where precedence --------------------------------------


def test_or_where_follows_sql_precedence_without_grouping():
    """AND binds tighter than OR: this is `a OR (b AND c)`."""
    sql, params = _select().where("a", 1).or_where("b", 2).where("c", 3).build()
    assert sql == "SELECT * FROM `u` WHERE `a` = %s OR `b` = %s AND `c` = %s"
    assert params == (1, 2, 3)


def test_condition_groups_an_or_inside_an_and():
    sql, params = (
        _select().where(Condition("a", 1) | Condition("b", 2)).where("c", 3).build()
    )
    assert sql == "SELECT * FROM `u` WHERE ((`a` = %s OR `b` = %s)) AND `c` = %s"
    assert params == (1, 2, 3)


def test_condition_groups_an_and_inside_an_or():
    sql, params = (
        _select()
        .where("x", 0)
        .or_where(Condition("a", 1) & Condition("b", 2))
        .build()
    )
    assert sql == "SELECT * FROM `u` WHERE `x` = %s OR ((`a` = %s AND `b` = %s))"
    assert params == (0, 1, 2)


def test_having_follows_the_same_rules():
    sql, _ = (
        _select()
        .group_by("g")
        .having(Condition("n>", 1) | Condition("m>", 2))
        .having("k", 3)
        .build()
    )
    assert sql.endswith("HAVING ((`n` > %s OR `m` > %s)) AND `k` = %s")
