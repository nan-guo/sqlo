import pytest

from sqlo import PostgreSQLDialect, Q, UnsupportedFeatureError, Window

pg = Q.using(PostgreSQLDialect())


def test_mysql_null_safe_equals_in_a_string_on_is_rejected_for_postgresql():
    with pytest.raises(UnsupportedFeatureError):
        pg.select("*").from_("a").join("b", "a.x <=> b.y")


def test_mysql_accepts_it_and_portable_operators_work_everywhere():
    sql, _ = Q.select("*").from_("a").join("b", "a.x <=> b.y").build()
    assert "ON a.x <=> b.y" in sql
    sql, _ = pg.select("*").from_("a").join("b", "a.x >= b.y AND a.z <> b.w").build()
    assert "ON a.x >= b.y AND a.z <> b.w" in sql


def test_update_and_delete_joins_check_the_operator_too():
    with pytest.raises(UnsupportedFeatureError):
        Q.using(PostgreSQLDialect()).select("*").from_("a").left_join(
            "b", "a.x <=> b.y"
        )


def test_a_cross_join_with_on_is_rejected():
    with pytest.raises(ValueError, match="CROSS JOIN"):
        Q.select("*").from_("a").join("b", "a.x = b.y", join_type="CROSS")


def test_a_cross_join_without_on_still_works():
    sql, _ = Q.select("*").from_("a").join("b", join_type="CROSS").build()
    assert sql == "SELECT * FROM `a` CROSS JOIN `b`"


def test_an_interval_bound_needs_a_range_frame():
    with pytest.raises(ValueError, match="range_between"):
        Window.order_by("ts").rows_between("INTERVAL 7 DAY PRECEDING", "CURRENT ROW")
    with pytest.raises(ValueError, match="range_between"):
        Window.order_by("ts").rows_between("1 PRECEDING", "INTERVAL 1 DAY FOLLOWING")


def test_an_interval_bound_works_in_a_range_frame():
    window = Window.order_by("ts").range_between(
        "INTERVAL 7 DAY PRECEDING", "CURRENT ROW"
    )
    assert "RANGE BETWEEN INTERVAL 7 DAY PRECEDING AND CURRENT ROW" in window.build(
        Q.get_dialect()
    )
