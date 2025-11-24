
from typing import Any, Dict, List, Optional, Tuple, Union

from ..expressions import ComplexCondition, Condition, Raw
from .base import Query
from .mixins import WhereClauseMixin


class UpdateQuery(WhereClauseMixin, Query):
    __slots__ = (
        "_table",
        "_values",
        "_wheres",
        "_limit",
        "_order_bys",
        "_joins",
        "_dialect",
    )

    def __init__(self, table: str, dialect=None):
        super().__init__(dialect)
        self._table = table
        self._values: Dict[str, Any] = {}
        self._wheres: List[Tuple[str, str, Any]] = []
        self._limit: Optional[int] = None
        self._order_bys: List[str] = []
        self._joins: List[Tuple[str, str, Optional[str]]] = (
            []
        )  # (type, table, on)

    def set(self, values: Dict[str, Any]) -> "UpdateQuery":
        self._values.update(values)
        return self

    def join(
        self, table: str, on: Optional[str] = None, join_type: str = "INNER"
    ) -> "UpdateQuery":
        """Add a JOIN clause (MySQL multi-table UPDATE)."""
        self._joins.append((join_type, table, on))
        return self

    def left_join(self, table: str, on: Optional[str] = None) -> "UpdateQuery":
        """Add a LEFT JOIN clause."""
        return self.join(table, on, join_type="LEFT")

    def where(
        self,
        column: Union[str, Raw, Condition, ComplexCondition],
        value: Any = None,
        operator: str = "=",
    ) -> "UpdateQuery":
        connector, sql, params = self._build_where_clause(
            column, value, operator
        )
        self._wheres.append((connector, sql, params))
        return self

    def limit(self, limit: int) -> "UpdateQuery":
        self._limit = limit
        return self

    def order_by(self, *columns: str) -> "UpdateQuery":
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
        if not self._values:
            raise ValueError("No values to update")

        parts: List[str] = []
        params: List[Any] = []
        ph = self._dialect.parameter_placeholder()

        # UPDATE table SET
        parts.append("UPDATE ")
        parts.append(self._dialect.quote(self._table))

        # JOINs (for multi-table UPDATE)
        if self._joins:
            for type_, table, on in self._joins:
                parts.append(f" {type_} JOIN {table}")
                if on:
                    parts.append(f" ON {on}")

        parts.append(" SET ")

        first = True
        for col, val in self._values.items():
            if not first:
                parts.append(", ")
            first = False
            parts.append(self._dialect.quote(col))
            parts.append(" = ")

            # Handle Raw expressions
            if isinstance(val, Raw):
                parts.append(val.sql)
                params.extend(val.params)
            # Handle subqueries
            elif hasattr(val, "build"):
                sub_sql, sub_params = val.build()
                parts.append(f"({sub_sql})")
                params.extend(sub_params)
            # Handle regular values
            else:
                parts.append(ph)
                params.append(val)

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
