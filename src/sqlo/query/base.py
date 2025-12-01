from abc import ABC, abstractmethod
from typing import Any, Optional

from ..dialects.base import Dialect
from ..dialects.mysql import MySQLDialect


class Query(ABC):
    """Abstract base class for all queries."""

    def __init__(self, dialect: Optional[Dialect] = None, debug: bool = False):
        self._dialect = dialect or MySQLDialect()
        self._debug = debug
        self._ph = self._dialect.parameter_placeholder()
        self._ctes: list[tuple[Any, str, bool]] = []  # (query, name, recursive)

    def with_(
        self, query: Any, name: Optional[str] = None, recursive: bool = False
    ) -> Any:
        """Add a Common Table Expression (CTE)."""
        if name is None:
            if hasattr(query, "_alias") and query._alias:
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
            if hasattr(query, "build"):
                sql, p = query.build()
                parts.append(sql)
                params.extend(p)
            else:
                parts.append(str(query))
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
