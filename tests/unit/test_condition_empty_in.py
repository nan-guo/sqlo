import pytest

from sqlo import Condition, Q


@pytest.mark.parametrize("empty", [[], ()])
def test_empty_in_is_false(empty):
    assert Condition.in_("a", empty).build() == ("FALSE", ())
    assert Condition("a", empty, operator="IN").build() == ("FALSE", ())


@pytest.mark.parametrize("empty", [[], ()])
def test_empty_not_in_is_true(empty):
    assert Condition.not_in("a", empty).build() == ("TRUE", ())
    assert Condition("a", empty, operator="NOT IN").build() == ("TRUE", ())


def test_empty_in_inside_a_query_matches_where_in():
    cond_sql, _ = Q.select("*").from_("u").where(Condition.in_("a", [])).build()
    func_sql, _ = Q.select("*").from_("u").where_in("a", []).build()
    assert cond_sql == "SELECT * FROM `u` WHERE (FALSE)"
    assert func_sql == "SELECT * FROM `u` WHERE FALSE"


def test_empty_in_combines_and_keeps_param_order():
    cond = Condition("x", 1) & Condition.in_("a", []) & Condition("y", 2)
    sql, params = cond.build()
    assert sql == "(`x` = %s AND FALSE AND `y` = %s)"
    assert params == (1, 2)


def test_empty_in_still_validates_the_column():
    with pytest.raises(ValueError):
        Condition.in_("a; DROP TABLE x", [])
