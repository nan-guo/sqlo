import pytest

from sqlo import Q

BREAKOUTS = [
    "MAX_EXECUTION_TIME(1) */ UNION SELECT password FROM users -- ",
    "INDEX(t i) */ ; DROP TABLE x; /*",
    "*/",
    "a */ b",
    "/* a",
    "INDEX(t i) /* nested",
]


@pytest.mark.parametrize("hint", BREAKOUTS)
def test_hints_that_could_leave_the_comment_are_rejected(hint):
    with pytest.raises(ValueError, match="comment"):
        Q.select("*").from_("u").optimizer_hint(hint)


@pytest.mark.parametrize("hint", [None, 1, ["INDEX(t i)"], b"INDEX(t i)"])
def test_non_string_hints_are_rejected(hint):
    with pytest.raises(TypeError):
        Q.select("*").from_("u").optimizer_hint(hint)


@pytest.mark.parametrize(
    "hint",
    [
        "INDEX(users idx_email)",
        "MAX_EXECUTION_TIME(1000)",
        "SET_VAR(sort_buffer_size = 16M)",
        "NO_RANGE_OPTIMIZATION(t1 PRIMARY, idx)",
        "JOIN_ORDER(t1, t2)",
        "BKA(t1) NO_BKA(t2)",
        "QB_NAME(qb1)",
        "a -- b",  # inert inside a block comment
        "a; b",  # inert inside a block comment
    ],
)
def test_ordinary_hints_are_accepted_and_stay_inside_the_comment(hint):
    sql, _ = Q.select("*").from_("u").optimizer_hint(hint).build()
    assert sql == f"SELECT /*+ {hint} */ * FROM `u`"
    assert sql.count("*/") == 1 and sql.count("/*") == 1


def test_a_rejected_hint_leaves_the_query_unchanged():
    q = Q.select("*").from_("u").optimizer_hint("INDEX(u i)")
    with pytest.raises(ValueError):
        q.optimizer_hint("x */ y")
    assert q.build()[0] == "SELECT /*+ INDEX(u i) */ * FROM `u`"
