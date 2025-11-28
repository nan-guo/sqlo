from .base import Dialect


class MySQLDialect(Dialect):
    """MySQL dialect implementation."""

    @property
    def quote_char(self) -> str:
        return "`"

    def parameter_placeholder(self) -> str:
        return "%s"
