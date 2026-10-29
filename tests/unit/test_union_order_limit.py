from sqlo import Q


def _u():
    return Q.select("id").from_("u")


def _v():
    return Q.select("id").from_("v")


def test_plain_union_is_unchanged():
    sql, _ = _u().union(_v()).build()
    assert sql == "SELECT `id` FROM `u` UNION SELECT `id` FROM `v`"
    sql, _ = _u().union_all(_v()).build()
    assert sql == "SELECT `id` FROM `u` UNION ALL SELECT `id` FROM `v`"


def test_order_and_limit_apply_to_the_whole_union():
    sql, _ = _u().union(_v()).order_by("-id").limit(10).build()
    assert sql == (
        "SELECT `id` FROM `u` UNION SELECT `id` FROM `v` ORDER BY `id` DESC LIMIT 10"
    )


def test_call_order_of_union_and_limit_does_not_matter():
    a, _ = _u().union(_v()).order_by("id").limit(10).build()
    b, _ = _u().order_by("id").limit(10).union(_v()).build()
    assert a == b


def test_offset_after_union():
    sql, _ = _u().union(_v()).limit(5).offset(10).build()
    assert sql == "SELECT `id` FROM `u` UNION SELECT `id` FROM `v` LIMIT 5 OFFSET 10"


def test_several_unions_then_limit():
    sql, _ = _u().union(_v()).union_all(Q.select("id").from_("w")).limit(5).build()
    assert sql == (
        "SELECT `id` FROM `u` UNION SELECT `id` FROM `v` "
        "UNION ALL SELECT `id` FROM `w` LIMIT 5"
    )


def test_union_operand_with_its_own_order_and_limit_is_parenthesized():
    sql, _ = _u().union(_v().order_by("id").limit(3)).build()
    assert sql == (
        "SELECT `id` FROM `u` UNION (SELECT `id` FROM `v` ORDER BY `id` ASC LIMIT 3)"
    )


def test_operand_limit_and_outer_limit_are_independent():
    sql, _ = _u().union_all(_v().limit(3)).order_by("id").limit(10).build()
    assert sql == (
        "SELECT `id` FROM `u` UNION ALL (SELECT `id` FROM `v` LIMIT 3) "
        "ORDER BY `id` ASC LIMIT 10"
    )


def test_operand_with_only_order_by_is_parenthesized():
    sql, _ = _u().union(_v().order_by("id")).build()
    assert sql == "SELECT `id` FROM `u` UNION (SELECT `id` FROM `v` ORDER BY `id` ASC)"


def test_params_keep_sql_order():
    q = _u().where("a", 1).union(_v().where("b", 2).limit(3)).where("c", 3)
    sql, params = q.limit(9).build()
    assert sql == (
        "SELECT `id` FROM `u` WHERE `a` = %s AND `c` = %s "
        "UNION (SELECT `id` FROM `v` WHERE `b` = %s LIMIT 3) LIMIT 9"
    )
    assert params == (1, 3, 2)


def test_limit_zero_after_union():
    sql, _ = _u().union(_v()).limit(0).build()
    assert sql.endswith("UNION SELECT `id` FROM `v` LIMIT 0")


def test_recursive_cte_union_all_is_unchanged():
    cte = (
        Q.select("id", "manager_id")
        .from_("employees")
        .where("id", 1)
        .union_all(Q.select("e.id", "e.manager_id").from_("employees", "e"))
        .as_("hierarchy")
    )
    sql, params = Q.select("*").with_(cte, recursive=True).from_("hierarchy").build()
    assert sql.startswith("WITH RECURSIVE `hierarchy` AS (SELECT `id`, `manager_id`")
    assert "UNION ALL SELECT `e`.`id`, `e`.`manager_id` FROM `employees` e)" in sql
    assert params == (1,)
