from sqlo import Condition, Q
from sqlo.expressions import ComplexCondition


def test_simple_condition():
    """Simple Condition with single clause"""
    cond = Condition("age >", 18)
    query = Q.select("*").from_("users").where(cond)
    sql, params = query.build()
    assert "`age` > %s" in sql
    assert params == (18,)


def test_condition_and():
    """Condition with AND (using &)"""
    cond = Condition("age >", 18) & Condition("country", "FR")
    query = Q.select("*").from_("users").where(cond)
    sql, params = query.build()
    assert "AND" in sql
    assert params == (18, "FR")


def test_condition_or():
    """Condition with OR (using |)"""
    cond = Condition("age >", 18) | Condition("vip", True)
    query = Q.select("*").from_("users").where(cond)
    sql, params = query.build()
    assert "OR" in sql
    assert params == (18, True)


def test_condition_complex_precedence():
    """Complex condition: (A AND B) OR C"""
    cond = (Condition("age >", 18) & Condition("country", "FR")) | Condition(
        "vip", True
    )
    query = Q.select("*").from_("users").where(cond)
    sql, params = query.build()
    assert "((`age` > %s AND `country` = %s) OR `vip` = %s)" in sql
    assert params == (18, "FR", True)


def test_condition_multiple_and():
    """Chaining multiple AND conditions"""
    cond = Condition("a", 1) & Condition("b", 2) & Condition("c", 3) & Condition("d", 4)
    query = Q.select("*").from_("users").where(cond)
    sql, params = query.build()
    assert "AND" in sql
    assert params == (1, 2, 3, 4)


def test_complex_condition_and():
    """ComplexCondition with AND"""
    cond1 = Condition("age >", 18) | Condition("vip", True)
    cond2 = Condition("country", "FR") | Condition("country", "US")
    complex_cond = cond1 & cond2

    query = Q.select("*").from_("users").where(complex_cond)
    sql, params = query.build()
    assert "AND" in sql
    assert params == (18, True, "FR", "US")


def test_complex_condition_or():
    """ComplexCondition with OR"""
    cond1 = Condition("status", "active") & Condition("verified", True)
    cond2 = Condition("admin", True)
    complex_cond = cond1 | cond2

    query = Q.select("*").from_("users").where(complex_cond)
    sql, params = query.build()
    assert "OR" in sql
    assert params == ("active", True, True)


def test_complex_condition_deep_nesting():
    """Deeply nested ComplexConditions: ((a AND b) OR c) AND d"""
    c1 = Condition("a", 1)
    c2 = Condition("b", 2)
    c3 = Condition("c", 3)
    c4 = Condition("d", 4)

    complex_cond = ((c1 & c2) | c3) & c4

    query = Q.select("*").from_("test").where(complex_cond)
    sql, params = query.build()
    assert params == (1, 2, 3, 4)


def test_complex_condition_standalone():
    """ComplexCondition created directly"""
    c1 = Condition("a", 1)
    c2 = Condition("b", 2)
    complex_cond = ComplexCondition("OR", c1, c2)

    query = Q.select("*").from_("test").where(complex_cond)
    sql, params = query.build()
    assert "OR" in sql
    assert params == (1, 2)
