from sqlo import Q, Raw, func


def test_select_basic():
    """Basic SELECT with WHERE"""
    query = Q.select("id", "name").from_("users").where("active", True)
    sql, params = query.build()
    assert sql == "SELECT `id`, `name` FROM `users` WHERE `active` = %s"
    assert params == (True,)


def test_select_all_columns():
    """SELECT * from table"""
    query = Q.select("*").from_("users")
    sql, _ = query.build()
    assert sql == "SELECT * FROM `users`"


def test_select_with_alias():
    """SELECT with table alias"""
    query = Q.select("u.id", "u.name").from_("users", alias="u")
    sql, _ = query.build()
    assert "FROM `users` u" in sql


def test_select_complex():
    """Complex SELECT with JOIN, WHERE, GROUP BY, ORDER BY, LIMIT"""
    query = (
        Q.select("u.id", func.count("o.id").as_("count"))
        .from_("users", alias="u")
        .left_join("orders o", on="u.id = o.user_id")
        .where("u.age >", 18)
        .group_by("u.id")
        .order_by("-count")
        .limit(10)
    )
    sql, params = query.build()
    assert "SELECT `u`.`id`, COUNT(o.id)" in sql
    assert "LEFT JOIN orders o ON u.id = o.user_id" in sql
    assert "WHERE `u`.`age` > %s" in sql
    assert "GROUP BY `u`.`id`" in sql
    assert "ORDER BY `count` DESC" in sql
    assert "LIMIT 10" in sql
    assert params == (18,)


def test_select_distinct():
    """SELECT DISTINCT"""
    query = Q.select("country").from_("users").distinct()
    sql, _ = query.build()
    assert sql == "SELECT DISTINCT `country` FROM `users`"


def test_select_distinct_multiple_columns():
    """SELECT DISTINCT with multiple columns"""
    query = Q.select("country", "city").from_("users").distinct()
    sql, _ = query.build()
    assert "SELECT DISTINCT `country`, `city`" in sql


def test_select_group_by():
    """SELECT with GROUP BY"""
    query = Q.select("country", func.count("id")).from_("users").group_by("country")
    sql, _ = query.build()
    assert "GROUP BY `country`" in sql


def test_select_group_by_multiple():
    """SELECT with GROUP BY multiple columns"""
    query = Q.select("country", "city").from_("users").group_by("country", "city")
    sql, _ = query.build()
    assert "GROUP BY `country`, `city`" in sql


def test_select_order_by_asc():
    """SELECT with ORDER BY ASC"""
    query = Q.select("*").from_("users").order_by("name")
    sql, _ = query.build()
    assert "ORDER BY `name` ASC" in sql


def test_select_order_by_desc():
    """SELECT with ORDER BY DESC"""
    query = Q.select("*").from_("users").order_by("-created_at")
    sql, _ = query.build()
    assert "ORDER BY `created_at` DESC" in sql


def test_select_order_by_multiple():
    """SELECT with multiple ORDER BY columns"""
    query = Q.select("*").from_("users").order_by("country", "-created_at", "name")
    sql, _ = query.build()
    assert "ORDER BY `country` ASC, `created_at` DESC, `name` ASC" in sql


def test_select_limit():
    """SELECT with LIMIT"""
    query = Q.select("*").from_("users").limit(10)
    sql, _ = query.build()
    assert "LIMIT 10" in sql


def test_select_limit_offset():
    """SELECT with LIMIT and OFFSET"""
    query = Q.select("*").from_("users").limit(10).offset(20)
    sql, _ = query.build()
    assert "LIMIT 10 OFFSET 20" in sql


def test_select_paginate():
    """SELECT with paginate helper"""
    query = Q.select("*").from_("users").paginate(page=2, per_page=25)
    sql, _ = query.build()
    assert "LIMIT 25 OFFSET 25" in sql


def test_select_paginate_first_page():
    """Paginate page=1 should have no OFFSET"""
    query = Q.select("*").from_("users").paginate(page=1, per_page=10)
    sql, _ = query.build()
    assert "LIMIT 10" in sql


def test_select_paginate_negative_page():
    """Paginate with page < 1 defaults to 1"""
    query = Q.select("*").from_("users").paginate(page=-5, per_page=10)
    sql, _ = query.build()
    assert "LIMIT 10" in sql


def test_select_force_index():
    """SELECT with FORCE INDEX"""
    q = Q.select("*").from_("users").force_index("idx_email")
    sql, _ = q.build()
    assert sql == "SELECT * FROM `users` FORCE INDEX (`idx_email`)"


def test_select_use_index_multiple():
    """SELECT with USE INDEX (multiple indexes)"""
    q = Q.select("*").from_("users").use_index("idx_a", "idx_b")
    sql, _ = q.build()
    assert sql == "SELECT * FROM `users` USE INDEX (`idx_a`, `idx_b`)"


def test_select_ignore_index():
    """SELECT with IGNORE INDEX"""
    q = Q.select("*").from_("users").ignore_index("idx_bad")
    sql, _ = q.build()
    assert sql == "SELECT * FROM `users` IGNORE INDEX (`idx_bad`)"


def test_select_explain():
    """SELECT with EXPLAIN"""
    q = Q.select("*").from_("users").where("id", 1).explain()
    sql, params = q.build()
    assert sql == "EXPLAIN SELECT * FROM `users` WHERE `id` = %s"
    assert params == (1,)


def test_select_union():
    """SELECT with UNION"""
    q1 = Q.select("id").from_("users").where("active", True)
    q2 = Q.select("id").from_("users").where("active", False)
    q_union = q1.union(q2)
    sql, params = q_union.build()
    assert "UNION" in sql
    assert params == (True, False)


def test_select_union_all():
    """SELECT with UNION ALL"""
    q1 = Q.select("id").from_("users").where("active", True)
    q2 = Q.select("id").from_("users").where("active", False)
    q_union_all = q1.union_all(q2)
    sql, params = q_union_all.build()
    assert "UNION ALL" in sql
    assert params == (True, False)


def test_select_when_true():
    """when() with True condition applies the lambda"""
    query = Q.select("*").from_("users").when(True, lambda q: q.where("active", True))
    sql, params = query.build()
    assert "WHERE `active` = %s" in sql
    assert params == (True,)


def test_select_when_false():
    """when() with False condition skips the lambda"""
    query = Q.select("*").from_("users").when(False, lambda q: q.where("active", True))
    sql, params = query.build()
    assert "WHERE" not in sql
    assert params == ()


def test_select_from_subquery():
    """SELECT from a subquery"""
    subquery = Q.select("id", "name").from_("users").where("active", True)
    query = Q.select("*").from_(subquery, alias="active_users")
    sql, params = query.build()
    assert (
        "(SELECT `id`, `name` FROM `users` WHERE `active` = %s) AS active_users" in sql
    )
    assert params == (True,)


def test_select_where_in_subquery():
    """WHERE IN with subquery"""
    sub = Q.select("id").from_("users").where("active", False)
    query = Q.select("email").from_("users").where_in("id", sub)
    sql, params = query.build()
    assert "WHERE `id` IN (SELECT `id` FROM `users` WHERE `active` = %s)" in sql
    assert params == (False,)


def test_select_where_in_list():
    """WHERE IN with list of values"""
    query = Q.select("*").from_("users").where_in("id", [1, 2, 3])
    sql, params = query.build()
    assert sql == "SELECT * FROM `users` WHERE `id` IN (%s, %s, %s)"
    assert params == (1, 2, 3)


def test_select_no_table_error():
    """SELECT without table should raise error"""
    import pytest

    query = Q.select("*")
    with pytest.raises(ValueError, match="No table specified"):
        query.build()


def test_select_from_subquery_alias():
    """SELECT from subquery using subquery's alias"""
    subquery = Q.select("id").from_("users").as_("u")
    query = Q.select("*").from_(subquery)
    sql, _ = query.build()
    assert "(SELECT `id` FROM `users` u) AS u" in sql


def test_select_overrides():
    """Test SelectQuery overrides for where methods"""
    q = Q.select("*").from_("users")

    # where_not_in
    q.where_not_in("id", [1, 2])
    sql, params = q.build()
    assert "NOT IN (%s, %s)" in sql
    assert params == (1, 2)

    # where_null
    q = Q.select("*").from_("users").where_null("deleted_at")
    sql, _ = q.build()
    assert "IS NULL" in sql

    # where_not_null
    q = Q.select("*").from_("users").where_not_null("email")
    sql, _ = q.build()
    assert "IS NOT NULL" in sql

    # where_between
    q = Q.select("*").from_("users").where_between("age", 18, 30)
    sql, params = q.build()
    assert "BETWEEN %s AND %s" in sql
    assert params == (18, 30)

    # where_not_between
    q = Q.select("*").from_("users").where_not_between("age", 0, 10)
    sql, params = q.build()
    assert "NOT BETWEEN %s AND %s" in sql
    assert params == (0, 10)

    # where_like
    q = Q.select("*").from_("users").where_like("name", "A%")
    sql, params = q.build()
    assert "LIKE %s" in sql
    assert params == ("A%",)

    # where_not_like
    q = Q.select("*").from_("users").where_not_like("name", "B%")
    sql, params = q.build()
    assert "NOT LIKE %s" in sql
    assert params == ("B%",)


def test_select_order_by_raw():
    """ORDER BY with Raw expression"""
    q = Q.select("*").from_("users").order_by(Raw("FIELD(status, 'active', 'pending')"))
    sql, _ = q.build()
    assert "ORDER BY FIELD(status, 'active', 'pending')" in sql


def test_select_raw_column():
    """SELECT with Raw column"""
    q = Q.select(Raw("COUNT(*) as count")).from_("users")
    sql, _ = q.build()
    assert "SELECT COUNT(*) as count FROM `users`" in sql


def test_select_as():
    """Test as_ method"""
    q = Q.select("*").from_("users").as_("u")
    assert q._alias == "u"


def test_select_with_list():
    """SELECT with columns as a list"""
    columns = ["id", "name", "email"]
    query = Q.select(columns).from_("users")
    sql, _ = query.build()
    assert sql == "SELECT `id`, `name`, `email` FROM `users`"


def test_select_with_list_and_alias():
    """SELECT with list of columns and table alias"""
    columns = ["u.id", "u.name"]
    query = Q.select(columns).from_("users", alias="u")
    sql, _ = query.build()
    assert "SELECT `u`.`id`, `u`.`name`" in sql
    assert "FROM `users` u" in sql


def test_select_with_empty_list():
    """SELECT with empty list defaults to *"""
    query = Q.select([]).from_("users")
    sql, _ = query.build()
    assert sql == "SELECT * FROM `users`"


def test_select_list_vs_unpacked():
    """Verify list and unpacked arguments produce same SQL"""
    # Using list
    q1 = Q.select(["id", "name"]).from_("users")
    sql1, params1 = q1.build()

    # Using unpacked arguments
    q2 = Q.select("id", "name").from_("users")
    sql2, params2 = q2.build()

    assert sql1 == sql2
    assert params1 == params2
