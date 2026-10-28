from typing import Any, Optional

from ..security import validate_non_negative_int
from .base import Query
from .mixins import JoinClauseMixin, WhereClauseMixin


class DeleteQuery(WhereClauseMixin, JoinClauseMixin, Query):
    def __init__(self, table: str, dialect=None, debug=False):
        super().__init__(dialect, debug)
        self._table = table
        self._wheres: list[tuple[str, str, Any]] = []
        self._limit: Optional[int] = None
        self._order_bys: list[str] = []
        self._joins: list[tuple[str, Any, str, tuple[Any, ...]]] = []
        self._allow_all_rows: bool = False

    def limit(self, limit: int) -> "DeleteQuery":
        self._limit = validate_non_negative_int(limit, "limit")
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

        # MySQL's multi-table DELETE has no ORDER BY or LIMIT
        if self._joins and (self._order_bys or self._limit is not None):
            raise ValueError(
                "ORDER BY and LIMIT cannot be used in a DELETE with a JOIN"
            )

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

        # DELETE FROM. With a JOIN the table to delete from is named first:
        # DELETE t FROM t JOIN ... (DELETE FROM t JOIN ... is a syntax error)
        table = self._dialect.quote(self._table)
        if self._joins:
            parts.append(f"DELETE {table} FROM {table}")
        else:
            parts.append(f"DELETE FROM {table}")

        # JOINs (for multi-table DELETE)
        self._build_joins(parts, params)

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
        if self._limit is not None:
            parts.append(f" LIMIT {self._limit}")

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
