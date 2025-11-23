from io import StringIO
from typing import Any, List, Optional, Tuple, Union

from ..expressions import Func, Raw
from .base import Query
from .mixins import WhereClauseMixin

# Cache for IN clause placeholders
_PLACEHOLDER_CACHE = {}


class SelectQuery(WhereClauseMixin, Query):
    __slots__ = (
        "_columns",
        "_table",
        "_alias",
        "_joins",
        "_wheres",
        "_groups",
        "_havings",
        "_orders",
        "_limit",
        "_offset",
        "_index_hint",
        "_explain",
        "_distinct",
        "_unions",
        "_dialect",
    )

    def __init__(self, *columns: Union[str, Raw, Func], dialect=None):
        super().__init__(dialect)
        self._columns = columns if columns else ["*"]
        self._table = None
        self._alias = None
        self._joins: List[Tuple[str, str, str]] = []  # (type, table, on)
        self._wheres: List[Tuple[str, str, Any]] = (
            []
        )  # (connector, sql, params)
        self._groups: List[str] = []
        self._havings: List[Tuple[str, str, Any]] = []
        self._orders: List[str] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._index_hint: Optional[Tuple[str, Tuple[str, ...]]] = None
        self._explain: bool = False
        self._distinct: bool = False
        self._unions: List[Tuple[str, "SelectQuery"]] = []

    def from_(
        self, table: Union[str, "SelectQuery"], alias: str = None
    ) -> "SelectQuery":
        self._table = table
        self._alias = alias
        return self

    def join(
        self, table: str, on: str = None, join_type: str = "INNER"
    ) -> "SelectQuery":
        self._joins.append((join_type, table, on))
        return self

    def inner_join(self, table: str, on: str = None) -> "SelectQuery":
        return self.join(table, on, join_type="INNER")

    def left_join(self, table: str, on: str = None) -> "SelectQuery":
        return self.join(table, on, join_type="LEFT")

    def right_join(self, table: str, on: str = None) -> "SelectQuery":
        return self.join(table, on, join_type="RIGHT")

    def cross_join(self, table: str) -> "SelectQuery":
        return self.join(table, on=None, join_type="CROSS")

    def where(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> "SelectQuery":
        connector, sql, params = self._build_where_clause(
            column, value, operator
        )
        self._wheres.append((connector, sql, params))
        return self

    def where_in(
        self, column: str, values: Union[List[Any], "SelectQuery"]
    ) -> "SelectQuery":
        if hasattr(values, "build"):  # Subquery
            sub_sql, sub_params = values.build()
            self._wheres.append(
                (
                    "AND",
                    f"{self._dialect.quote(column)} IN ({sub_sql})",
                    sub_params,
                )
            )
        else:
            count = len(values)
            # Use cached placeholders for common sizes
            if count not in _PLACEHOLDER_CACHE:
                ph = self._dialect.parameter_placeholder()
                _PLACEHOLDER_CACHE[count] = ", ".join([ph] * count)
            placeholders = _PLACEHOLDER_CACHE[count]
            self._wheres.append(
                (
                    "AND",
                    f"{self._dialect.quote(column)} IN ({placeholders})",
                    tuple(values),
                )
            )
        return self

    def order_by(self, *columns: str) -> "SelectQuery":
        for col in columns:
            direction = "ASC"
            if col.startswith("-"):
                direction = "DESC"
                col = col[1:]
            self._orders.append(f"{self._dialect.quote(col)} {direction}")
        return self

    # _build_condition is now provided by WhereClauseMixin

    def limit(self, limit: int) -> "SelectQuery":
        self._limit = limit
        return self

    def offset(self, offset: int) -> "SelectQuery":
        self._offset = offset
        return self

    def group_by(self, *columns: str) -> "SelectQuery":
        self._groups.extend(map(self._dialect.quote, columns))
        return self

    def when(self, condition: Any, callback: callable) -> "SelectQuery":
        if condition:
            callback(self)
        return self

    def paginate(self, page: int, per_page: int) -> "SelectQuery":
        page = max(page, 1)  # Use max() builtin
        self._limit = per_page
        self._offset = (page - 1) * per_page
        return self

    def force_index(self, *indexes: str) -> "SelectQuery":
        self._index_hint = ("FORCE", indexes)
        return self

    def use_index(self, *indexes: str) -> "SelectQuery":
        self._index_hint = ("USE", indexes)
        return self

    def ignore_index(self, *indexes: str) -> "SelectQuery":
        self._index_hint = ("IGNORE", indexes)
        return self

    def explain(self) -> "SelectQuery":
        self._explain = True
        return self

    def distinct(self) -> "SelectQuery":
        self._distinct = True
        return self

    def having(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> "SelectQuery":
        connector, sql, params = self._build_where_clause(
            column, value, operator
        )
        self._havings.append((connector, sql, params))
        return self

    def union(self, query: "SelectQuery") -> "SelectQuery":
        self._unions.append(("UNION", query))
        return self

    def union_all(self, query: "SelectQuery") -> "SelectQuery":
        self._unions.append(("UNION ALL", query))
        return self

    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        if not self._table:
            raise ValueError("No table specified")

        buf = StringIO()
        params: List[Any] = []  # Use explicit type annotation

        # EXPLAIN
        if self._explain:
            buf.write("EXPLAIN ")

        # SELECT
        buf.write("SELECT")

        # DISTINCT
        if self._distinct:
            buf.write(" DISTINCT")

        # Columns
        buf.write(" ")
        first = True
        for col in self._columns:
            if not first:
                buf.write(", ")
            first = False

            if isinstance(col, Raw):
                buf.write(col.sql)
                params.extend(col.params)
            elif isinstance(col, Func):
                buf.write(f"{col.name}({', '.join(map(str, col.args))})")
            else:
                buf.write(self._dialect.quote(col) if col != "*" else "*")

        # FROM
        buf.write(" FROM ")
        if hasattr(self._table, "build"):  # Subquery
            sub_sql, sub_params = self._table.build()
            buf.write(f"({sub_sql})")
            params.extend(sub_params)
        else:
            buf.write(self._dialect.quote(self._table))

        if self._alias:
            buf.write(f" {self._alias}")

        # Index Hints
        if self._index_hint:
            hint_type, indexes = self._index_hint
            buf.write(f" {hint_type} INDEX (")
            buf.write(", ".join(map(self._dialect.quote, indexes)))
            buf.write(")")

        # Joins
        for type_, table, on in self._joins:
            buf.write(f" {type_} JOIN {table}")
            if on:
                buf.write(f" ON {on}")

        # Where
        if self._wheres:
            buf.write(" WHERE ")
            for i, (connector, sql, p) in enumerate(self._wheres):
                if i > 0:
                    buf.write(f" {connector} ")
                buf.write(sql)
                params.extend(p)

        # Group By
        if self._groups:
            buf.write(" GROUP BY ")
            buf.write(", ".join(self._groups))

        # Having
        if self._havings:
            buf.write(" HAVING ")
            for i, (connector, sql, p) in enumerate(self._havings):
                if i > 0:
                    buf.write(f" {connector} ")
                buf.write(sql)
                params.extend(p)

        # Order By
        if self._orders:
            buf.write(" ORDER BY ")
            buf.write(", ".join(self._orders))

        # Limit/Offset
        if self._limit is not None:
            buf.write(" ")
            buf.write(self._dialect.limit_offset(self._limit, self._offset))

        # Unions
        if self._unions:
            for type_, query in self._unions:
                union_sql, union_params = query.build()
                buf.write(f" {type_} {union_sql}")
                params.extend(union_params)

        return buf.getvalue(), tuple(params)
