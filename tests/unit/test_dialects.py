from sqlo.dialects.mysql import MySQLDialect


def test_quote_simple_identifier():
    """Quote simple identifier"""
    dialect = MySQLDialect()
    quoted = dialect.quote("username")
    assert quoted == "`username`"


def test_quote_dotted_identifier():
    """Quote dotted identifier (table.column)"""
    dialect = MySQLDialect()
    quoted = dialect.quote("users.id")
    assert quoted == "`users`.`id`"


def test_parameter_placeholder():
    """MySQL uses %s as parameter placeholder"""
    dialect = MySQLDialect()
    assert dialect.parameter_placeholder() == "%s"


def test_limit_offset_with_offset():
    """LIMIT with OFFSET"""
    dialect = MySQLDialect()
    result = dialect.limit_offset(10, 20)
    assert result == "LIMIT 10 OFFSET 20"


def test_limit_offset_without_offset():
    """LIMIT without OFFSET (offset=0)"""
    dialect = MySQLDialect()
    result = dialect.limit_offset(10, 0)
    assert result == "LIMIT 10"
