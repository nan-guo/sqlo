from io import StringIO
from typing import Any, Dict, List, Tuple, Union

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
        "_dialect",
    )

    def __init__(self, table: str, dialect=None):
        super().__init__(dialect)
        self._table = table
        self._values: Dict[str, Any] = {}
        self._wheres: List[Tuple[str, str, Any]] = []
        self._limit: int = None
        self._order_bys: List[str] = []

    def set(self, values: Dict[str, Any]) -> "UpdateQuery":
        self._values.update(values)
        return self

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

    # _build_condition is now provided by WhereClauseMixin

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

        buf = StringIO()
        params: List[Any] = []  # Use explicit type annotation
        ph = self._dialect.parameter_placeholder()

        # UPDATE table SET
        buf.write("UPDATE ")
        buf.write(self._dialect.quote(self._table))
        buf.write(" SET ")

        first = True
        for col, val in self._values.items():
            if not first:
                buf.write(", ")
            first = False
            buf.write(self._dialect.quote(col))
            buf.write(" = ")
            buf.write(ph)
            params.append(val)

        # WHERE
        if self._wheres:
            buf.write(" WHERE ")
            for i, (connector, sql, p) in enumerate(self._wheres):
                if i > 0:
                    buf.write(f" {connector} ")
                buf.write(sql)
                params.extend(p)

        # ORDER BY
        if self._order_bys:
            buf.write(" ORDER BY ")
            buf.write(", ".join(self._order_bys))

        # LIMIT
        if self._limit:
            buf.write(f" LIMIT {self._limit}")

        return buf.getvalue(), tuple(params)
