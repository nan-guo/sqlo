import pytest

from sqlo import JSON, Func, Q, Raw, Window, func

BAD_STR_ARGS = [
    "*; DROP TABLE x",
    "id) FROM users; DROP TABLE x; --",
    "DISTINCT id",
    "a b",
    "'x'",
    "",
    "1a",
]


# --- Func -------------------------------------------------------------


@pytest.mark.parametrize("arg", BAD_STR_ARGS)
def test_func_rejects_unsafe_string_args(arg):
    with pytest.raises(ValueError):
        Func("COUNT", arg)


@pytest.mark.parametrize("arg", BAD_STR_ARGS)
def test_window_func_rejects_unsafe_string_args(arg):
    with pytest.raises(ValueError):
        func.lag(arg, 1).over(Window.order_by("id"))


@pytest.mark.parametrize("name", ["COUNT(*); DROP TABLE x; --", "a b", "", "a.b", "1a"])
def test_func_rejects_invalid_name(name):
    with pytest.raises(ValueError):
        Func(name, "id")


def test_func_factory_rejects_invalid_name():
    with pytest.raises(ValueError):
        getattr(func, "count; drop")("id")


def test_func_rejects_unsupported_arg_type():
    with pytest.raises(TypeError):
        Func("COUNT", object())
    with pytest.raises(TypeError):
        Func("COUNT", ["id"])


def test_func_rejects_non_finite_float():
    with pytest.raises(ValueError):
        Func("ROUND", "price", float("nan"))
    with pytest.raises(ValueError):
        Func("ROUND", "price", float("inf"))


def test_func_rejects_raw_with_params():
    with pytest.raises(ValueError):
        Func("COALESCE", "a", Raw("%s", [1]))


@pytest.mark.parametrize(
    "f, expected",
    [
        (func.count("*"), "COUNT(*)"),
        (func.count(), "COUNT(*)"),
        (func.sum("o.amount"), "SUM(o.amount)"),
        (func.ntile(4), "NTILE(4)"),
        (func.lag("value", 1), "LAG(value, 1)"),
        (func.round("price", 2), "ROUND(price, 2)"),
        (func.round("price", 1.5), "ROUND(price, 1.5)"),
        (func.ifnull("a", None), "IFNULL(a, NULL)"),
        (func.coalesce("a", True), "COALESCE(a, TRUE)"),
        (func.count(Raw("DISTINCT id")), "COUNT(DISTINCT id)"),
        (func.coalesce(func.sum("s.amount"), 0), "COALESCE(SUM(s.amount), 0)"),
        (func.row_number(), "ROW_NUMBER()"),
    ],
)
def test_valid_func_args_render(f, expected):
    sql, _ = Q.select(f).from_("t").build()
    assert sql == f"SELECT {expected} FROM `t`"


def test_valid_func_alias_still_works():
    sql, _ = Q.select(func.count("*").as_("c")).from_("t").build()
    assert sql == "SELECT COUNT(*) AS `c` FROM `t`"


def test_window_func_args_render():
    f = func.lead("value", 2).over(Window.partition_by("d").and_order_by("-x"))
    sql, _ = Q.select(f.as_("n")).from_("t").build()
    assert sql == (
        "SELECT LEAD(value, 2) OVER (PARTITION BY `d` ORDER BY `x` DESC) AS `n` "
        "FROM `t`"
    )


# --- JSONPath ---------------------------------------------------------

BAD_JSON_PATHS = [
    "a' OR '1'='1",
    "a'; DROP TABLE x; --",
    "a b",
    "",
    "a..b",
    ".a",
    "a.",
    "a[x]",
    "a[0",
    "a\"b",
    "$.a",
    "a->b",
]


@pytest.mark.parametrize("path", BAD_JSON_PATHS)
def test_jsonpath_rejects_unsafe_paths(path):
    with pytest.raises(ValueError):
        JSON("d").extract(path)


@pytest.mark.parametrize(
    "path",
    [
        "name",
        "user.preferences.theme",
        "orders[0].items[0].category",
        "items[0].name",
        "[0]",
        "a",
        "tags[*]",
        "*",
        "a.*",
        "user_id",
    ],
)
def test_jsonpath_valid_paths_unchanged(path):
    sql, _ = Q.select(JSON("d").extract(path)).from_("t").build()
    assert sql == f"SELECT `d`->>'$.{path}' FROM `t`"
    sql, params = Q.select("*").from_("t").where(JSON("d").extract(path), 1).build()
    assert sql == f"SELECT * FROM `t` WHERE `d`->>'$.{path}' = %s"
    assert params == (1,)


# --- Window frame -----------------------------------------------------

BAD_FRAME_BOUNDS = [
    "CURRENT ROW) ; DROP TABLE x; --",
    "1 PRECEDING AND 2 FOLLOWING) --",
    "UNBOUNDED",
    "PRECEDING",
    "-1 PRECEDING",
    "x PRECEDING",
    "1; DROP FOLLOWING",
    "",
    "INTERVAL 1 FORTNIGHT PRECEDING",
    "INTERVAL x DAY PRECEDING",
]


@pytest.mark.parametrize("bound", BAD_FRAME_BOUNDS)
def test_rows_between_rejects_bad_bounds(bound):
    with pytest.raises(ValueError):
        Window.order_by("id").rows_between(bound, "CURRENT ROW")
    with pytest.raises(ValueError):
        Window.order_by("id").rows_between("CURRENT ROW", bound)


@pytest.mark.parametrize("bound", BAD_FRAME_BOUNDS)
def test_range_between_rejects_bad_bounds(bound):
    with pytest.raises(ValueError):
        Window.order_by("id").range_between(bound, "CURRENT ROW")
    with pytest.raises(ValueError):
        Window.order_by("id").range_between("CURRENT ROW", bound)


@pytest.mark.parametrize(
    "start, end",
    [
        ("UNBOUNDED PRECEDING", "CURRENT ROW"),
        ("UNBOUNDED PRECEDING", "UNBOUNDED FOLLOWING"),
        ("6 PRECEDING", "CURRENT ROW"),
        ("CURRENT ROW", "2 FOLLOWING"),
        ("INTERVAL 7 DAY PRECEDING", "CURRENT ROW"),
    ],
)
def test_valid_frames_render(start, end):
    w = Window.order_by("d").rows_between(start, end)
    assert w.build(Q.select("*")._dialect).endswith(f"ROWS BETWEEN {start} AND {end}")


def test_frame_bounds_are_normalized():
    w = Window.order_by("d").range_between("unbounded   preceding", "current row")
    sql = w.build(Q.select("*")._dialect)
    assert sql.endswith("RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW")
