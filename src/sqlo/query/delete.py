from io import StringIO
from typing import Any, List, Tuple, Union

from ..expressions import ComplexCondition, Condition, Raw
from .base import Query
from .mixins import WhereClauseMixin


class DeleteQuery(WhereClauseMixin, Query):
    __slots__ = ("_table", "_wheres", "_limit", "_order_bys", "_dialect")

    def __init__(self, table: str, dialect=None):
        super().__init__(dialect)
        self._table = table
        self._wheres: List[Tuple[str, str, Any]] = []
        self._limit: int = None
        self._order_bys: List[str] = []

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

    # _build_condition is now provided by WhereClauseMixin

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

        buf = StringIO()
        params: List[Any] = []

        # DELETE FROM
        buf.write("DELETE FROM ")
        buf.write(self._dialect.quote(self._table))

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
