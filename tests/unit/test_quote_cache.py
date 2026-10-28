import pytest

from sqlo.dialects.base import Dialect, _quote_identifier
from sqlo.dialects.mysql import MySQLDialect


class AnsiDialect(Dialect):
    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "?"


def test_quoting_is_unchanged():
    d = MySQLDialect()
    assert d.quote("users") == "`users`"
    assert d.quote("users.id") == "`users`.`id`"
    assert d.quote("db.users.id") == "`db`.`users`.`id`"


def test_dialects_with_different_quote_chars_do_not_share_results():
    mysql, ansi = MySQLDialect(), AnsiDialect()
    for _ in range(2):  # the second round is served from the cache
        assert mysql.quote("a.b") == "`a`.`b`"
        assert ansi.quote("a.b") == '"a"."b"'


def test_a_changing_quote_char_is_respected():
    class Switching(AnsiDialect):
        char = '"'

        @property
        def quote_char(self) -> str:
            return self.char

    d = Switching()
    assert d.quote("a") == '"a"'
    d.char = "'"
    assert d.quote("a") == "'a'"


@pytest.mark.parametrize("bad", ["a; DROP TABLE x", "a b", "", "1a", "a`b"])
def test_invalid_identifiers_are_rejected_every_time(bad):
    d = MySQLDialect()
    for _ in range(3):
        with pytest.raises(ValueError, match="Invalid identifier"):
            d.quote(bad)


@pytest.mark.parametrize("bad", [None, 1, 1.5, ["a"], ("a",), {"a"}, object()])
def test_non_string_identifiers_raise_value_error_not_type_error(bad):
    with pytest.raises(ValueError, match="Invalid identifier"):
        MySQLDialect().quote(bad)


def test_a_valid_identifier_is_not_forgotten_after_an_invalid_one():
    d = MySQLDialect()
    assert d.quote("a") == "`a`"
    with pytest.raises(ValueError):
        d.quote("a; b")
    assert d.quote("a") == "`a`"


def test_the_cache_is_bounded():
    info = _quote_identifier.cache_info()
    assert info.maxsize is not None and info.maxsize > 0


def test_repeated_quotes_hit_the_cache():
    d = MySQLDialect()
    d.quote("cache_probe_column")
    before = _quote_identifier.cache_info().hits
    d.quote("cache_probe_column")
    assert _quote_identifier.cache_info().hits == before + 1


def test_a_subclass_overriding_quote_is_not_affected():
    class Custom(MySQLDialect):
        def quote(self, identifier: str) -> str:
            return f"<{identifier}>"

    assert Custom().quote("a") == "<a>"
