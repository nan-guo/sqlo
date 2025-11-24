from sqlo import Q


def test_inner_join():
    """INNER JOIN"""
    query = (
        Q.select("u.id", "u.name", "o.total")
        .from_("users", alias="u")
        .inner_join("orders o", on="u.id = o.user_id")
    )
    sql, _ = query.build()
    assert "INNER JOIN orders o ON u.id = o.user_id" in sql


def test_left_join():
    """LEFT JOIN"""
    query = (
        Q.select("u.id", "u.name", "o.total")
        .from_("users", alias="u")
        .left_join("orders o", on="u.id = o.user_id")
    )
    sql, _ = query.build()
    assert "LEFT JOIN orders o ON u.id = o.user_id" in sql


def test_right_join():
    """RIGHT JOIN"""
    query = (
        Q.select("u.id", "u.name", "o.total")
        .from_("users", alias="u")
        .right_join("orders o", on="u.id = o.user_id")
    )
    sql, _ = query.build()
    assert "RIGHT JOIN orders o ON u.id = o.user_id" in sql


def test_cross_join():
    """CROSS JOIN"""
    query = (
        Q.select("u.id", "p.name").from_("users", alias="u").cross_join("products p")
    )
    sql, _ = query.build()
    assert "CROSS JOIN products p" in sql


def test_multiple_joins():
    """Multiple different JOIN types in one query"""
    query = (
        Q.select("u.id", "o.total", "p.name")
        .from_("users", alias="u")
        .inner_join("orders o", on="u.id = o.user_id")
        .left_join("payments p", on="o.id = p.order_id")
        .right_join("addresses a", on="u.id = a.user_id")
        .where("u.active", True)
    )
    sql, params = query.build()

    assert "INNER JOIN orders o ON u.id = o.user_id" in sql
    assert "LEFT JOIN payments p ON o.id = p.order_id" in sql
    assert "RIGHT JOIN addresses a ON u.id = a.user_id" in sql
    assert params == (True,)


def test_generic_join_method():
    """Generic join() method with custom JOIN type"""
    query = (
        Q.select("*")
        .from_("users")
        .join("orders", on="users.id = orders.user_id", join_type="FULL OUTER")
    )
    sql, _ = query.build()
    assert "FULL OUTER JOIN orders ON users.id = orders.user_id" in sql
