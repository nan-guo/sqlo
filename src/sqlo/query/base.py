from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

from ..dialects.base import Dialect
from ..dialects.mysql import MySQLDialect
from ..expressions import Raw


_T = TypeVar("_T", bound="Query")


def _clone_element(element: Any) -> Any:
    """Clone a nested query, or the queries held in a clause tuple.

    Clause tuples such as ``(type, table, on)``, ``(type, query)`` and
    ``(query, name, recursive)`` are rebuilt one level deep. Anything else,
    including the rendered parameters of a WHERE clause, is shared: nothing
    modifies it after it is created.
    """
    if isinstance(element, Query):
        return element.clone()
    if isinstance(element, tuple):
        return tuple(e.clone() if isinstance(e, Query) else e for e in element)
    return element


class Query(ABC):
    """Abstract base class for all queries."""

    def __init__(self, dialect: Optional[Dialect] = None, debug: bool = False):
        self._dialect = dialect or MySQLDialect()
        self._debug = debug
        self._ph = self._dialect.parameter_placeholder()
        self._ctes: list[tuple[Any, str, bool]] = []  # (query, name, recursive)

    def clone(self: _T) -> _T:
        """Return an independent copy of this query.

        Queries are mutable: every method changes the query and returns it, so
        two queries derived from the same base would share their conditions.
        Clone the base first to branch from it::

            base = Q.select("*").from_("users").where("active", True)
            adults = base.clone().where("age >", 18)
            french = base.clone().where("country", "FR")

        Lists and dicts are copied and nested queries (a subquery in FROM or
        JOIN, UNION operands, CTEs, ...) are cloned too. The dialect and the
        expression objects (``Raw``, ``Condition``, ...) are shared.
        """
        clone = object.__new__(type(self))
        for name, value in self.__dict__.items():
            if isinstance(value, list):
                value = [_clone_element(e) for e in value]
            elif isinstance(value, dict):
                value = {k: _clone_element(e) for k, e in value.items()}
            else:
                value = _clone_element(value)
            setattr(clone, name, value)
        return clone

    def with_(
        self, query: Any, name: Optional[str] = None, recursive: bool = False
    ) -> Any:
        """Add a Common Table Expression (CTE).

        Args:
            query: A query builder, or ``Raw`` for SQL written by hand. Plain
                strings are rejected: use ``Raw`` to mark SQL as trusted.
            name: The CTE name. Defaults to the alias of ``query``.
            recursive: Whether this is a recursive CTE.
        """
        if not isinstance(query, (Query, Raw)):
            raise TypeError(
                "A CTE must be a query builder or Raw(), "
                f"got {type(query).__name__}"
            )
        if name is None:
            if isinstance(query, Query) and query._alias:
                name = query._alias
            else:
                raise ValueError("CTE name must be provided")
        self._ctes.append((query, name, recursive))
        return self

    def _build_ctes(self, parts: list[str], params: list[Any]) -> None:
        """Build CTEs clause."""
        if not self._ctes:
            return

        parts.append("WITH ")
        if any(recursive for _, _, recursive in self._ctes):
            parts.append("RECURSIVE ")

        first = True
        for query, name, _ in self._ctes:
            if not first:
                parts.append(", ")
            first = False

            parts.append(f"{self._dialect.quote(name)} AS (")
            if isinstance(query, Raw):
                parts.append(query.sql)
                params.extend(query.params)
            else:
                sql, p = query.build()
                parts.append(sql)
                params.extend(p)
            parts.append(")")

        parts.append(" ")

    def _print_debug(self, sql: str, params: tuple[Any, ...]) -> None:
        """Print debug output if debug mode is enabled."""
        if self._debug:
            print(f"[sqlo DEBUG] {sql}")
            print(f"[sqlo DEBUG] Params: {params}")

    def debug(self) -> Any:
        """Print the SQL and parameters to stdout."""
        sql, params = self.build()
        print(f"[sqlo DEBUG] {sql}")
        print(f"[sqlo DEBUG] Params: {params}")
        return self

    @abstractmethod
    def build(self) -> tuple[str, tuple[Any, ...]]:
        """Build the query and return (sql, params)."""
        raise NotImplementedError("Subclasses must implement build()")

    def __str__(self) -> str:
        """Return the compiled SQL string (for debugging)."""
        sql, _ = self.build()
        return sql
