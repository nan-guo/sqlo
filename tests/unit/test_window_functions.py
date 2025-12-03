"""Tests for window function support."""

from sqlo import Q, Window, func


def test_window_function_basic():
    """Test basic window function with ROW_NUMBER."""
    q = Q.select(
        "name",
        "department",
        func.row_number().over(Window.partition_by("department")).as_("row_num"),
    ).from_("employees")

    sql, params = q.build()

    assert "ROW_NUMBER() OVER (PARTITION BY `department`)" in sql
    assert "AS `row_num`" in sql
    assert params == ()


def test_window_function_with_order():
    """Test window function with ORDER BY."""
    q = Q.select(
        "name",
        "salary",
        func.rank()
        .over(Window.partition_by("department").and_order_by("-salary"))
        .as_("rank"),
    ).from_("employees")

    sql, params = q.build()

    assert "RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC)" in sql
    assert "AS `rank`" in sql


def test_window_function_order_only():
    """Test window function with ORDER BY only (no PARTITION BY)."""
    q = Q.select(
        "name", func.row_number().over(Window.order_by("created_at")).as_("seq")
    ).from_("users")

    sql, _ = q.build()

    assert "ROW_NUMBER() OVER (ORDER BY `created_at` ASC)" in sql


def test_window_function_empty_over():
    """Test window function with empty OVER clause."""
    q = Q.select("name", func.count("*").over().as_("total")).from_("users")

    sql, _ = q.build()

    assert "COUNT(*) OVER ()" in sql


def test_window_function_with_frame():
    """Test window function with frame clause."""
    q = Q.select(
        "date",
        "amount",
        func.sum("amount")
        .over(
            Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
        )
        .as_("running_total"),
    ).from_("transactions")

    sql, _ = q.build()

    assert (
        "SUM(amount) OVER (ORDER BY `date` ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)"
        in sql
    )


def test_window_function_multiple():
    """Test multiple window functions in same query."""
    q = Q.select(
        "name",
        "department",
        func.row_number().over(Window.partition_by("department")).as_("row_num"),
        func.rank()
        .over(Window.partition_by("department").and_order_by("-salary"))
        .as_("rank"),
    ).from_("employees")

    sql, _ = q.build()

    assert "ROW_NUMBER() OVER (PARTITION BY `department`)" in sql
    assert "RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC)" in sql


def test_window_function_lag_lead():
    """Test LAG and LEAD window functions."""
    q = Q.select(
        "date",
        "value",
        func.lag("value", 1).over(Window.order_by("date")).as_("prev_value"),
        func.lead("value", 1).over(Window.order_by("date")).as_("next_value"),
    ).from_("metrics")

    sql, _ = q.build()

    assert "LAG(value, 1) OVER (ORDER BY `date` ASC)" in sql
    assert "LEAD(value, 1) OVER (ORDER BY `date` ASC)" in sql


def test_window_function_ntile():
    """Test NTILE window function."""
    q = Q.select(
        "name",
        "salary",
        func.ntile(4).over(Window.order_by("-salary")).as_("quartile"),
    ).from_("employees")

    sql, _ = q.build()

    assert "NTILE(4) OVER (ORDER BY `salary` DESC)" in sql


def test_window_function_and_partition_by():
    """Test adding partition columns with and_partition_by()."""
    window = Window.partition_by("department").and_partition_by("location")
    q = Q.select("name", func.row_number().over(window).as_("row_num")).from_(
        "employees"
    )

    sql, _ = q.build()

    assert "PARTITION BY `department`, `location`" in sql


def test_window_function_range_between():
    """Test RANGE BETWEEN frame clause."""
    q = Q.select(
        "date",
        "amount",
        func.sum("amount")
        .over(
            Window.order_by("date").range_between("UNBOUNDED PRECEDING", "CURRENT ROW")
        )
        .as_("running_total"),
    ).from_("transactions")

    sql, _ = q.build()

    assert "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW" in sql
