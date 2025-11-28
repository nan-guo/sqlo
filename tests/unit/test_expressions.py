from sqlo import Q, Raw, func


def test_raw_expression():
    """Raw SQL expression in WHERE"""
    query = Q.select("*").from_("users").where(Raw("YEAR(created_at) = %s", [2023]))
    sql, params = query.build()
    assert "YEAR(created_at) = %s" in sql
    assert params == (2023,)


def test_raw_in_having():
    """Raw SQL in HAVING clause"""
    query = (
        Q.select("category", func.count("id"))
        .from_("products")
        .group_by("category")
        .having(Raw("COUNT(id) > 100", []))
    )
    sql, params = query.build()
    assert "HAVING COUNT(id) > 100" in sql
    assert params == ()


def test_func_count():
    """func.count() creates COUNT function"""
    query = Q.select(func.count("id")).from_("users")
    sql, _ = query.build()
    assert "COUNT(id)" in sql


def test_func_with_alias():
    """Func aliasing with as_()"""
    query = Q.select(func.count("id").as_("total_users")).from_("users")
    sql, _ = query.build()
    assert "COUNT(id)" in sql


def test_function_factory():
    """FunctionFactory creates SQL functions dynamically"""
    # Test common SQL functions
    assert func.max("price").name == "MAX"
    assert func.min("price").name == "MIN"
    assert func.avg("price").name == "AVG"
    assert func.sum("price").name == "SUM"
    assert func.count("*").name == "COUNT"

    # Test custom function names
    assert func.custom_func("arg").name == "CUSTOM_FUNC"


def test_function_factory_private_attribute():
    """Accessing private attributes raises AttributeError"""
    import pytest

    with pytest.raises(AttributeError):
        _ = func._private_attr
