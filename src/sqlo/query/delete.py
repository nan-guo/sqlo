from typing import Any, Optional, Union

from ..expressions import ComplexCondition, Condition, Raw
from .base import Query
from .mixins import WhereClauseMixin


class DeleteQuery(WhereClauseMixin, Query):
    __slots__ = (
        "_table",
        "_wheres",
        "_limit",
        "_order_bys",
        "_joins",
        "_dialect",
        "_allow_all_rows",
    )

    def __init__(self, table: str, dialect=None, debug=False):
        super().__init__(dialect, debug)
        self._table = table
        self._wheres: list[tuple[str, str, Any]] = []
        self._limit: Optional[int] = None
        self._order_bys: list[str] = []
        self._joins: list[tuple[str, str, Optional[str]]] = []  # (type, table, on)
        self._allow_all_rows: bool = False

    def join(
        self, table: str, on: Optional[str] = None, join_type: str = "INNER"
    ) -> "DeleteQuery":
        """Add a JOIN clause (MySQL multi-table DELETE)."""
        self._joins.append((join_type, table, on))
        return self

    def left_join(self, table: str, on: Optional[str] = None) -> "DeleteQuery":
        """Add a LEFT JOIN clause."""
        return self.join(table, on, join_type="LEFT")

    def where(
        self,
        column: Union[str, Raw, Condition, ComplexCondition],
        value: Any = None,
        operator: str = "=",
    ) -> "DeleteQuery":
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append((connector, sql, params))
        return self

    def limit(self, limit: int) -> "DeleteQuery":
        self._limit = limit
        return self

    def order_by(self, *columns: str) -> "DeleteQuery":
        for col in columns:
            direction = "ASC"
            if col.startswith("-"):
                direction = "DESC"
                col = col[1:]
            self._order_bys.append(f"{self._dialect.quote(col)} {direction}")
        return self

    def allow_all_rows(self) -> "DeleteQuery":
        """Allow DELETE without WHERE clause (deletes all rows).

        This is a safety feature to prevent accidental mass deletions.
        You must call this method explicitly if you want to delete all rows.

        Returns:
            Self for method chaining

        Example:
            >>> Q.delete_from("temp_table").allow_all_rows().build()
        """
        self._allow_all_rows = True
        return self

    def build(self) -> tuple[str, tuple[Any, ...]]:
        if not self._table:
            raise ValueError("No table specified")

        # Safety check: DELETE without WHERE
        if not self._wheres and not self._allow_all_rows:
            raise ValueError(
                "DELETE without WHERE clause would affect all rows. "
                "If this is intentional, call .allow_all_rows() first."
            )

        parts: list[str] = []
        params: list[Any] = []

        # CTEs
        self._build_ctes(parts, params)

        # DELETE FROM
        parts.append("DELETE FROM ")
        parts.append(self._dialect.quote(self._table))

        # JOINs (for multi-table DELETE)
        if self._joins:
            for type_, table, on in self._joins:
                parts.append(f" {type_} JOIN {table}")
                if on:
                    parts.append(f" ON {on}")

        # WHERE
        if self._wheres:
            parts.append(" WHERE ")
            for i, (connector, sql, p) in enumerate(self._wheres):
                if i > 0:
                    parts.append(f" {connector} ")
                parts.append(sql)
                params.extend(p)

        # ORDER BY
        if self._order_bys:
            parts.append(" ORDER BY ")
            parts.append(", ".join(self._order_bys))

        # LIMIT
        if self._limit:
            parts.append(f" LIMIT {self._limit}")

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
