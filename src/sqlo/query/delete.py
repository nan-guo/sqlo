
from typing import Any, List, Optional, Tuple, Union

from ..expressions import ComplexCondition, Condition, Raw
from .base import Query
from .mixins import WhereClauseMixin


class DeleteQuery(WhereClauseMixin, Query):
    __slots__ = ("_table", "_wheres", "_limit", "_order_bys", "_joins", "_dialect")

    def __init__(self, table: str, dialect=None):
        super().__init__(dialect)
        self._table = table
        self._wheres: List[Tuple[str, str, Any]] = []
        self._limit: Optional[int] = None
        self._order_bys: List[str] = []
        self._joins: List[Tuple[str, str, Optional[str]]] = (
            []
        )  # (type, table, on)

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
        connector, sql, params = self._build_where_clause(
            column, value, operator
        )
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

    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        if not self._table:
            raise ValueError("No table specified")

        parts: List[str] = []
        params: List[Any] = []

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

        return "".join(parts), tuple(params)
