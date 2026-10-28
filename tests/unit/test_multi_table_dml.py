import pytest

from sqlo import Condition, Q, Raw

# --- DELETE with JOIN uses the multi-table syntax MySQL accepts -------------


def test_delete_with_join_names_the_target_before_from():
    sql, params = (
        Q.delete_from("users")
        .join("orders", "orders.user_id = users.id")
        .where("users.id", 1)
        .build()
    )
    assert sql == (
        "DELETE `users` FROM `users` INNER JOIN orders ON orders.user_id = users.id "
        "WHERE `users`.`id` = %s"
    )
    assert params == (1,)


def test_delete_with_left_join():
    sql, _ = (
        Q.delete_from("users")
        .left_join("orders", "orders.user_id = users.id")
        .where_null("orders.id")
        .build()
    )
    assert sql == (
        "DELETE `users` FROM `users` LEFT JOIN orders ON orders.user_id = users.id "
        "WHERE `orders`.`id` IS NULL"
    )


def test_delete_with_several_joins():
    sql, _ = (
        Q.delete_from("t1")
        .join("t2", "t1.id = t2.id")
        .left_join("t3", "t2.id = t3.id")
        .where("t1.a", 1)
        .build()
    )
    assert sql == (
        "DELETE `t1` FROM `t1` INNER JOIN t2 ON t1.id = t2.id "
        "LEFT JOIN t3 ON t2.id = t3.id WHERE `t1`.`a` = %s"
    )


def test_delete_join_params_come_before_where_params():
    sql, params = (
        Q.delete_from("u")
        .join("v", Raw("v.k = %s", ["k"]))
        .where("u.id", 5)
        .build()
    )
    assert sql == (
        "DELETE `u` FROM `u` INNER JOIN v ON v.k = %s WHERE `u`.`id` = %s"
    )
    assert params == ("k", 5)


def test_delete_join_with_a_condition_and_a_cte():
    on = Condition("v.uid", Raw("u.id")) & Condition("v.flag", True)
    sql, params = (
        Q.delete_from("u")
        .with_(Raw("SELECT %s AS n", [7]), "c")
        .join("v", on)
        .where("u.id", 5)
        .build()
    )
    assert sql == (
        "WITH `c` AS (SELECT %s AS n) DELETE `u` FROM `u` "
        "INNER JOIN v ON (`v`.`uid` = u.id AND `v`.`flag` = %s) WHERE `u`.`id` = %s"
    )
    assert params == (7, True, 5)


def test_delete_without_a_join_is_unchanged():
    assert Q.delete_from("users").where("id", 1).build() == (
        "DELETE FROM `users` WHERE `id` = %s",
        (1,),
    )
    assert Q.delete_from("users").allow_all_rows().build() == (
        "DELETE FROM `users`",
        (),
    )


def test_delete_without_a_join_keeps_order_by_and_limit():
    sql, _ = Q.delete_from("users").where("id", 1).order_by("id").limit(5).build()
    assert sql == "DELETE FROM `users` WHERE `id` = %s ORDER BY `id` ASC LIMIT 5"


def test_delete_join_still_needs_a_where_or_allow_all_rows():
    q = Q.delete_from("u").join("v", "u.id = v.id")
    with pytest.raises(ValueError, match="without WHERE"):
        q.build()
    sql, _ = q.allow_all_rows().build()
    assert sql == "DELETE `u` FROM `u` INNER JOIN v ON u.id = v.id"


# --- ORDER BY and LIMIT are not allowed together with JOIN -------------------


@pytest.mark.parametrize(
    "configure",
    [
        lambda q: q.order_by("id"),
        lambda q: q.limit(5),
        lambda q: q.limit(0),
        lambda q: q.order_by("id").limit(5),
    ],
)
def test_delete_with_join_rejects_order_by_and_limit(configure):
    q = Q.delete_from("u").join("v", "u.id = v.id").where("u.id", 1)
    configure(q)
    with pytest.raises(ValueError, match="DELETE.*JOIN"):
        q.build()


@pytest.mark.parametrize(
    "configure",
    [
        lambda q: q.order_by("id"),
        lambda q: q.limit(5),
        lambda q: q.limit(0),
        lambda q: q.order_by("id").limit(5),
    ],
)
def test_update_with_join_rejects_order_by_and_limit(configure):
    q = Q.update("u").set({"a": 1}).join("v", "u.id = v.id").where("u.id", 1)
    configure(q)
    with pytest.raises(ValueError, match="UPDATE.*JOIN"):
        q.build()


def test_update_with_join_alone_is_unchanged():
    sql, params = (
        Q.update("u").set({"a": 1}).join("v", "u.id = v.id").where("u.id", 2).build()
    )
    assert sql == (
        "UPDATE `u` INNER JOIN v ON u.id = v.id SET `a` = %s WHERE `u`.`id` = %s"
    )
    assert params == (1, 2)


def test_update_without_a_join_keeps_order_by_and_limit():
    sql, _ = Q.update("u").set({"a": 1}).where("id", 1).order_by("id").limit(5).build()
    assert sql == "UPDATE `u` SET `a` = %s WHERE `id` = %s ORDER BY `id` ASC LIMIT 5"
