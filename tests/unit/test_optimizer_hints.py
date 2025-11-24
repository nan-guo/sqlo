from sqlo import Q


def test_optimizer_hint():
    """Optimizer hint"""
    query = Q.select("*").from_("users").optimizer_hint("INDEX(users idx_age)")
    sql, params = query.build()
    assert "SELECT /*+ INDEX(users idx_age) */ *" in sql
    assert params == ()


def test_multiple_optimizer_hints():
    """Multiple optimizer hints"""
    query = (
        Q.select("*")
        .from_("users")
        .optimizer_hint("INDEX(users idx_age)")
        .optimizer_hint("MAX_EXECUTION_TIME(1000)")
    )
    sql, params = query.build()
    assert "SELECT /*+ INDEX(users idx_age) MAX_EXECUTION_TIME(1000) */ *" in sql
    assert params == ()
