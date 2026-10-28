import pytest

from sqlo import Condition, Q, Raw


def _cte():
    return Q.select("id").from_("u").where("k", 1)


@pytest.mark.parametrize(
    "bad",
    ["SELECT 1", "SELECT 1; DROP TABLE x", "", None, 1, {"a": 1}, ["a"], Condition("a", 1)],
)
def test_with_rejects_anything_but_a_query_or_raw(bad):
    with pytest.raises(TypeError, match="query"):
        Q.select("*").from_("c").with_(bad, "c")
    with pytest.raises(TypeError, match="query"):
        Q.update("t").set({"a": 1}).with_(bad, "c")


def test_a_rejected_cte_leaves_the_query_unchanged():
    q = Q.select("*").from_("c")
    with pytest.raises(TypeError):
        q.with_("SELECT 1", "c")
    assert q.build()[0] == "SELECT * FROM `c`"


def test_query_ctes_keep_working():
    sql, params = Q.select("*").from_("c").with_(_cte(), "c").build()
    assert sql == "WITH `c` AS (SELECT `id` FROM `u` WHERE `k` = %s) SELECT * FROM `c`"
    assert params == (1,)


def test_the_name_defaults_to_the_alias_of_the_query():
    sql, _ = Q.select("*").from_("c").with_(_cte().as_("c")).build()
    assert sql.startswith("WITH `c` AS (")


def test_an_explicit_name_overrides_the_alias():
    sql, _ = Q.select("*").from_("d").with_(_cte().as_("c"), "d").build()
    assert sql.startswith("WITH `d` AS (")


def test_a_query_cte_without_a_name_or_alias_is_rejected():
    with pytest.raises(ValueError, match="CTE name"):
        Q.select("*").from_("c").with_(_cte())


def test_raw_cte_renders_its_sql_and_params_in_order():
    sql, params = (
        Q.select("*")
        .from_("c")
        .with_(Raw("SELECT %s AS n", [1]), "c")
        .where("n", 2)
        .build()
    )
    assert sql == "WITH `c` AS (SELECT %s AS n) SELECT * FROM `c` WHERE `n` = %s"
    assert params == (1, 2)


def test_raw_cte_needs_a_name():
    with pytest.raises(ValueError, match="CTE name"):
        Q.select("*").from_("c").with_(Raw("SELECT 1"))


def test_raw_and_query_ctes_can_be_mixed_and_keep_param_order():
    sql, params = (
        Q.select("*")
        .from_("a")
        .with_(Raw("SELECT %s AS n", ["raw"]), "a")
        .with_(_cte(), "c")
        .where("z", "main")
        .build()
    )
    assert sql == (
        "WITH `a` AS (SELECT %s AS n), `c` AS (SELECT `id` FROM `u` WHERE `k` = %s) "
        "SELECT * FROM `a` WHERE `z` = %s"
    )
    assert params == ("raw", 1, "main")


def test_raw_ctes_work_for_every_query_type():
    raw = Raw("SELECT %s AS n", [7])
    sql, params = Q.update("t").set({"a": 1}).with_(raw, "c").where("id", 2).build()
    assert sql == "WITH `c` AS (SELECT %s AS n) UPDATE `t` SET `a` = %s WHERE `id` = %s"
    assert params == (7, 1, 2)
    sql, params = Q.delete_from("t").with_(raw, "c").where("id", 2).build()
    assert sql == "WITH `c` AS (SELECT %s AS n) DELETE FROM `t` WHERE `id` = %s"
    assert params == (7, 2)


def test_cte_name_is_still_validated():
    q = Q.select("*").from_("c").with_(_cte(), "bad name")
    with pytest.raises(ValueError, match="Invalid identifier"):
        q.build()
