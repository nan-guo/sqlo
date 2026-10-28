from typing import Any, Union

from . import _debug
from .dialects.mysql import MySQLDialect
from .expressions import Func, Raw
from .query.delete import DeleteQuery
from .query.insert import InsertQuery
from .query.select import SelectQuery
from .query.update import UpdateQuery


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
