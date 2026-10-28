from typing import Any, Union

from . import _debug
from .dialects.base import Dialect
from .dialects.mysql import MySQLDialect
from .expressions import Func, Raw
from .query.delete import DeleteQuery
from .query.insert import InsertQuery
from .query.select import SelectQuery
from .query.update import UpdateQuery


class QueryFactory:
    """Creates queries for one dialect, independently of ``Q.set_dialect()``.

    Get one with ``Q.using(dialect)``::

        pg = Q.using(PostgreSQLDialect())
        pg.select("id").from_("users").build()
    """

    def __init__(self, dialect: Dialect):
        self.dialect = dialect

    def select(self, *columns: Union[str, Raw, Func]) -> SelectQuery[Any]:
        return SelectQuery(*columns, dialect=self.dialect)

    def insert_into(self, table: str) -> InsertQuery:
        return InsertQuery(table, dialect=self.dialect)

    def update(self, table: str) -> UpdateQuery:
        return UpdateQuery(table, dialect=self.dialect)

    def delete_from(self, table: str) -> DeleteQuery:
        return DeleteQuery(table, dialect=self.dialect)

    @staticmethod
    def raw(sql: str, params: Any = None) -> Raw:
        return Raw(sql, params)


class Q:
    """Query Builder Factory."""

    _default_dialect = MySQLDialect()

    @classmethod
    def set_debug(cls, debug: bool = True, hide_params: bool = False):
        """Enable or disable debug mode: print every built query to stdout.

        Queries are logged on the ``sqlo`` logger at DEBUG level (the SQL) and
        on ``sqlo.params`` (the parameters). This is a shortcut that attaches a
        stdout handler; the logger can also be configured like any other, and
        it applies to queries created before and after the call.

        Parameters can hold sensitive values such as passwords. Pass
        ``hide_params=True`` to leave them out, or give the ``sqlo.params``
        logger a higher level.
        """
        if debug:
            _debug.enable(hide_params=hide_params)
        else:
            _debug.disable()

    @classmethod
    def set_dialect(cls, dialect):
        """Set the default dialect for all queries."""
        cls._default_dialect = dialect

    @classmethod
    def get_dialect(cls):
        """Get the current default dialect."""
        return cls._default_dialect

    @staticmethod
    def using(dialect: Dialect) -> QueryFactory:
        """A query factory bound to ``dialect``, leaving the global default alone.

        The queries it creates, and the subqueries inside them, use that dialect,
        so one program can build MySQL and PostgreSQL queries side by side.
        """
        if isinstance(dialect, type) or not isinstance(dialect, Dialect):
            hint = (
                f" Pass an instance: {dialect.__name__}()."
                if isinstance(dialect, type)
                else ""
            )
            raise TypeError(
                f"Q.using() needs a Dialect instance, got {dialect!r}.{hint}"
            )
        return QueryFactory(dialect)

    @staticmethod
    def select(*columns: Union[str, Raw, Func]) -> SelectQuery[Any]:
        return SelectQuery(*columns, dialect=Q._default_dialect)

    @staticmethod
    def insert_into(table: str) -> InsertQuery:
        return InsertQuery(table, dialect=Q._default_dialect)

    @staticmethod
    def update(table: str) -> UpdateQuery:
        return UpdateQuery(table, dialect=Q._default_dialect)

    @staticmethod
    def delete_from(table: str) -> DeleteQuery:
        return DeleteQuery(table, dialect=Q._default_dialect)

    @staticmethod
    def raw(sql: str, params: Any = None) -> Raw:
        return Raw(sql, params)
