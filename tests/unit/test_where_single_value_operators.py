import pytest

from sqlo import Q


@pytest.mark.parametrize(
    "column, value, operator, helper",
    [
        ("id IN", [1, 2], "=", "where_in"),
        ("id", [1, 2], "IN", "where_in"),
        ("id", [1, 2], "not in", "where_not_in"),
        ("d", 1, "IS NULL", "where_null"),
        ("d", 1, "IS NOT NULL", "where_not_null"),
        ("d IS", "x", "=", "where_null"),
        ("d", "x", "IS NOT", "where_not_null"),
    ],
)
def test_where_rejects_operators_that_do_not_take_one_value(
    column, value, operator, helper
):
    with pytest.raises(ValueError, match=helper):
        Q.select("*").from_("t").where(column, value, operator)


def test_having_and_update_and_delete_reject_them_too():
    with pytest.raises(ValueError, match="where_in"):
        Q.select("a").from_("t").group_by("a").having("a IN", [1])
    with pytest.raises(ValueError, match="where_in"):
        Q.update("t").set({"a": 1}).where("id IN", [1])
    with pytest.raises(ValueError, match="where_in"):
        Q.delete_from("t").where("id IN", [1])


def test_the_helpers_still_work():
    sql, params = Q.select("*").from_("t").where_in("id", [1, 2]).build()
    assert sql == "SELECT * FROM `t` WHERE `id` IN (%s, %s)"
    sql, _ = Q.select("*").from_("t").where_null("d").build()
    assert sql == "SELECT * FROM `t` WHERE `d` IS NULL"
