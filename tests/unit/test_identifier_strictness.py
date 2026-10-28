import pytest

from sqlo import JSON, Condition, Q
from sqlo.dialects.mysql import MySQLDialect
from sqlo.security import validate_alias, validate_identifier

EMPTY_SEGMENTS = ["a..b", "a.", ".a", "a...b", "db..users.id", "users."]
TRAILING_WHITESPACE = ["users\n", "a.b\n", "a\r", "a\r\n", "a\t", "a "]


@pytest.mark.parametrize("ident", EMPTY_SEGMENTS)
def test_empty_segments_are_rejected(ident):
    assert validate_identifier(ident) is False


@pytest.mark.parametrize("ident", TRAILING_WHITESPACE + ["a\n.b", "\na"])
def test_whitespace_is_rejected(ident):
    assert validate_identifier(ident) is False
    assert validate_identifier(ident, allow_dot=False) is False


@pytest.mark.parametrize(
    "ident",
    ["users", "users.id", "db.users.id", "a_b", "_a", "A1", "a.1b", "a.b_2"],
)
def test_valid_identifiers_are_still_accepted(ident):
    assert validate_identifier(ident) is True


@pytest.mark.parametrize("ident", EMPTY_SEGMENTS + TRAILING_WHITESPACE)
def test_quote_rejects_them(ident):
    with pytest.raises(ValueError, match="Invalid identifier"):
        MySQLDialect().quote(ident)


@pytest.mark.parametrize("alias", ["x\n", "x ", "a.b"])
def test_aliases_reject_whitespace_and_dots(alias):
    with pytest.raises(ValueError):
        validate_alias(alias)
    with pytest.raises(ValueError):
        Q.select("*").from_("u", alias)


@pytest.mark.parametrize("ident", ["a..b", "a.", "users\n"])
def test_queries_reject_them(ident):
    with pytest.raises(ValueError, match="Invalid identifier"):
        Q.select(ident).from_("u").build()
    with pytest.raises(ValueError, match="Invalid identifier"):
        Q.select("*").from_(ident).build()
    with pytest.raises(ValueError, match="Invalid identifier"):
        Q.select("*").from_("u").where(ident, 1)
    with pytest.raises(ValueError, match="Invalid identifier"):
        Q.select("*").from_("u").where_in(ident, [1])
    with pytest.raises(ValueError, match="Invalid identifier"):
        Q.select("*").from_("u").order_by(ident)
    with pytest.raises(ValueError, match="Invalid identifier"):
        Condition(ident, 1)


@pytest.mark.parametrize("path", ["a\n", "a.b\n", "a\r\n"])
def test_json_path_rejects_trailing_newline(path):
    with pytest.raises(ValueError):
        JSON("d").extract(path)


@pytest.mark.parametrize("column", ["age>\n", "age>=\n"])
def test_compact_operator_does_not_silently_drop_a_trailing_newline(column):
    with pytest.raises(ValueError):
        Q.select("*").from_("u").where(column, 1)
    with pytest.raises(ValueError):
        Condition(column, 1)


def test_compact_operator_still_works():
    sql, _ = Q.select("*").from_("u").where("age>=", 1).build()
    assert sql == "SELECT * FROM `u` WHERE `age` >= %s"
