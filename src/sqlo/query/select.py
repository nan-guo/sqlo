from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, TypeVar, Union

from ..expressions import Func, JSONPath, Raw
from .base import Query
from .mixins import WhereClauseMixin

if TYPE_CHECKING:
    from ..expressions import ComplexCondition, Condition

T = TypeVar("T")


class SelectQuery(WhereClauseMixin, Query, Generic[T]):
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
        "_optimizer_hints",
    )

    def __init__(
        self, *columns: Union[str, Raw, Func, list], dialect=None, debug=False
    ):
        super().__init__(dialect, debug)
        # Support both Q.select("a", "b") and Q.select(["a", "b"])
        if len(columns) == 1 and isinstance(columns[0], list):
            self._columns = tuple(columns[0]) if columns[0] else ("*",)
        else:
            self._columns = columns if columns else ("*",)
        self._table: Optional[Union[str, SelectQuery]] = None
        self._alias: Optional[str] = None
        self._joins: list[tuple[str, str, Optional[str]]] = []  # (type, table, on)
        self._wheres: list[tuple[str, str, Any]] = []  # (connector, sql, params)
        self._groups: list[str] = []
        self._havings: list[tuple[str, str, Any]] = []
        self._orders: list[str] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._index_hint: Optional[tuple[str, tuple[str, ...]]] = None
        self._explain: bool = False
        self._distinct: bool = False
        self._unions: list[tuple[str, SelectQuery]] = []
        self._optimizer_hints: list[str] = []

    def from_(
        self, table: Union[str, "SelectQuery"], alias: Optional[str] = None
    ) -> "SelectQuery":
        self._table = table
        # If table is a subquery with its own alias, use that alias
        # Otherwise use the provided alias
        if hasattr(table, "_alias") and table._alias and alias is None:
            self._alias = table._alias
        else:
            self._alias = alias
        return self

    def join(
        self, table: str, on: Optional[str] = None, join_type: str = "INNER"
    ) -> "SelectQuery":
        # Validate table name (unless it's a subquery)
        if not isinstance(table, SelectQuery):
            # Extract table name from "table_name alias" format
            # e.g., "orders o" -> validate "orders"
            table_name = table.split()[0] if " " in table else table
            # This will raise ValueError if invalid
            self._dialect.quote(table_name)
        self._joins.append((join_type, table, on))
        return self

    def inner_join(self, table: str, on: Optional[str] = None) -> "SelectQuery[T]":
        return self.join(table, on, join_type="INNER")

    def left_join(self, table: str, on: Optional[str] = None) -> "SelectQuery[T]":
        return self.join(table, on, join_type="LEFT")

    def right_join(self, table: str, on: Optional[str] = None) -> "SelectQuery[T]":
        return self.join(table, on, join_type="RIGHT")

    def cross_join(self, table: str) -> "SelectQuery[T]":
        return self.join(table, on=None, join_type="CROSS")

    def where(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> "SelectQuery[T]":
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append((connector, sql, params))
        return self

    def where_in(
        self, column: str, values: Union[list[Any], "SelectQuery"]
    ) -> "SelectQuery[T]":
        """Add an IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=False)

    def where_not_in(
        self, column: str, values: Union[list[Any], "SelectQuery"]
    ) -> "SelectQuery[T]":
        """Add a NOT IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=True)

    def or_where(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> "SelectQuery[T]":
        """Add an OR WHERE condition."""
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append(("OR", sql, params))
        return self

    def where_null(self, column: str) -> "SelectQuery[T]":
        """Add an IS NULL WHERE condition."""
        self._wheres.append(("AND", f"{self._dialect.quote(column)} IS NULL", []))
        return self

    def where_not_null(self, column: str) -> "SelectQuery[T]":
        """Add an IS NOT NULL WHERE condition."""
        self._wheres.append(("AND", f"{self._dialect.quote(column)} IS NOT NULL", []))
        return self

    def where_between(self, column: str, value1: Any, value2: Any) -> "SelectQuery[T]":
        """Add a BETWEEN WHERE condition."""
        ph = self._ph
        self._wheres.append(
            (
                "AND",
                f"{self._dialect.quote(column)} BETWEEN {ph} AND {ph}",
                [value1, value2],
            )
        )
        return self

    def where_not_between(
        self, column: str, value1: Any, value2: Any
    ) -> "SelectQuery[T]":
        """Add a NOT BETWEEN WHERE condition."""
        ph = self._ph
        self._wheres.append(
            (
                "AND",
                f"{self._dialect.quote(column)} NOT BETWEEN {ph} AND {ph}",
                [value1, value2],
            )
        )
        return self

    def where_like(self, column: str, pattern: str) -> "SelectQuery[T]":
        """Add a LIKE WHERE condition."""
        return self.where(column, pattern, operator="LIKE")

    def where_not_like(self, column: str, pattern: str) -> "SelectQuery[T]":
        """Add a NOT LIKE WHERE condition."""
        return self.where(column, pattern, operator="NOT LIKE")

    def order_by(self, *columns: Union[str, Raw]) -> "SelectQuery[T]":
        for col in columns:
            if isinstance(col, Raw):
                self._orders.append(col.sql)
            else:
                direction = "ASC"
                if col.startswith("-"):
                    direction = "DESC"
                    col = col[1:]
                self._orders.append(f"{self._dialect.quote(col)} {direction}")
        return self

    def limit(self, limit: int) -> "SelectQuery[T]":
        self._limit = limit
        return self

    def offset(self, offset: int) -> "SelectQuery[T]":
        self._offset = offset
        return self

    def group_by(self, *columns: str) -> "SelectQuery[T]":
        self._groups.extend(map(self._dialect.quote, columns))
        return self

    def when(
        self, condition: Any, callback: Callable[["SelectQuery[T]"], None]
    ) -> "SelectQuery[T]":
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

    def optimizer_hint(self, hint: str) -> "SelectQuery":
        """Add an optimizer hint (MySQL 8.0+)."""
        self._optimizer_hints.append(hint)
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
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._havings.append((connector, sql, params))
        return self

    def union(self, query: "SelectQuery") -> "SelectQuery[T]":
        self._unions.append(("UNION", query))
        return self

    def union_all(self, query: "SelectQuery") -> "SelectQuery[T]":
        self._unions.append(("UNION ALL", query))
        return self

    def as_(self, alias: str) -> "SelectQuery":
        """Set an alias for this query (used in FROM clauses)."""
        self._alias = alias
        return self

    def _build_select_columns(self, parts: list[str], params: list[Any]) -> None:
        """Build SELECT columns clause."""
        parts.append(" ")
        first = True
        for col in self._columns:
            if not first:
                parts.append(", ")
            first = False

            if isinstance(col, Raw):
                parts.append(col.sql)
                params.extend(col.params)
            elif isinstance(col, Func):
                parts.append(f"{col.name}({', '.join(map(str, col.args))})")
            elif isinstance(col, JSONPath):
                parts.append(f"{self._dialect.quote(col.column)}->>'$.{col.path}'")
            # Handle WindowFunc
            elif hasattr(col, "build") and hasattr(col, "window"):
                parts.append(col.build(self._dialect))
            # Allow * and numeric literals without validation
            elif col == "*" or (isinstance(col, str) and col.isdigit()):
                parts.append(col)
            else:
                parts.append(self._dialect.quote(col))

            # Handle aliasing
            if hasattr(col, "alias") and col.alias:
                parts.append(f" AS {self._dialect.quote(col.alias)}")

    def _build_from_clause(self, parts: list[str], params: list[Any]) -> None:
        """Build FROM clause."""
        parts.append(" FROM ")
        if self._table and hasattr(self._table, "build"):  # Subquery
            # Get subquery's alias if it has one, otherwise use our alias
            subquery_alias = None
            if hasattr(self._table, "_alias"):
                subquery_alias = self._table._alias
            if subquery_alias is None:
                subquery_alias = self._alias

            sub_sql, sub_params = self._table.build()  # type: ignore[union-attr]
            parts.append(f"({sub_sql})")
            params.extend(sub_params)
            # For subqueries, use AS keyword for alias
            if subquery_alias:
                parts.append(f" AS {subquery_alias}")
        else:
            parts.append(self._dialect.quote(self._table))  # type: ignore[arg-type]
            # For regular tables, alias without AS (MySQL style)
            if self._alias:
                parts.append(f" {self._alias}")

        # Index Hints
        if self._index_hint:
            hint_type, indexes = self._index_hint
            parts.append(f" {hint_type} INDEX (")
            parts.append(", ".join(map(self._dialect.quote, indexes)))
            parts.append(")")

    def _build_joins(self, parts: list[str]) -> None:
        """Build JOIN clauses."""
        for type_, table, on in self._joins:
            parts.append(f" {type_} JOIN {table}")
            if on:
                parts.append(f" ON {on}")

    @staticmethod
    def _build_where_having(
        parts: list[str], params: list[Any], clauses: list, keyword: str
    ) -> None:
        """Build WHERE or HAVING clause."""
        if clauses:
            parts.append(f" {keyword} ")
            for i, (connector, sql, p) in enumerate(clauses):
                if i > 0:
                    parts.append(f" {connector} ")
                parts.append(sql)
                params.extend(p)

    def build(self) -> tuple[str, tuple[Any, ...]]:
        if not self._table:
            raise ValueError("No table specified")

        parts: list[str] = []
        params: list[Any] = []

        # EXPLAIN
        if self._explain:
            parts.append("EXPLAIN ")

        # CTEs
        self._build_ctes(parts, params)

        # SELECT
        parts.append("SELECT")

        # Optimizer Hints
        if self._optimizer_hints:
            parts.append(f" /*+ {' '.join(self._optimizer_hints)} */")

        # DISTINCT
        if self._distinct:
            parts.append(" DISTINCT")

        # Columns
        self._build_select_columns(parts, params)

        # FROM
        self._build_from_clause(parts, params)

        # Joins
        self._build_joins(parts)

        # Where
        self._build_where_having(parts, params, self._wheres, "WHERE")

        # Group By
        if self._groups:
            parts.append(" GROUP BY ")
            parts.append(", ".join(self._groups))

        # Having
        self._build_where_having(parts, params, self._havings, "HAVING")

        # Order By
        if self._orders:
            parts.append(" ORDER BY ")
            parts.append(", ".join(self._orders))

        # Limit/Offset
        if self._limit is not None:
            parts.append(" ")
            parts.append(self._dialect.limit_offset(self._limit, self._offset))

        # Unions
        if self._unions:
            for type_, query in self._unions:
                union_sql, union_params = query.build()
                parts.append(f" {type_} {union_sql}")
                params.extend(union_params)

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
