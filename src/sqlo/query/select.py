from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, TypeVar, Union

from ..expressions import Func, JSONPath, Raw, render_func
from .base import Query
from ..security import validate_alias, validate_non_negative_int
from .mixins import JoinClauseMixin, WhereClauseMixin

if TYPE_CHECKING:
    from ..expressions import ComplexCondition, Condition

T = TypeVar("T")
JoinOn = Union[str, Raw, "Condition", "ComplexCondition", None]


class SelectQuery(WhereClauseMixin, JoinClauseMixin, Query, Generic[T]):
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
        # Two different aliases: this query's own name when it is embedded in
        # another query (a subquery, JOIN or CTE), and the alias of the table in
        # this query's own FROM clause.
        self._alias: Optional[str] = None
        self._table_alias: Optional[str] = None
        self._joins: list[tuple[str, Any, str, tuple[Any, ...]]] = []
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
        if alias is not None:
            validate_alias(alias)
        self._table = table
        # The alias of the table (or derived table) in this FROM clause. For a
        # subquery without an explicit alias, its own alias (``as_()``) is used.
        self._table_alias = alias
        return self

    def inner_join(self, table: str, on: JoinOn = None) -> "SelectQuery[T]":
        return self.join(table, on, join_type="INNER")

    def right_join(self, table: str, on: JoinOn = None) -> "SelectQuery[T]":
        return self.join(table, on, join_type="RIGHT")

    def cross_join(self, table: str) -> "SelectQuery[T]":
        return self.join(table, on=None, join_type="CROSS")

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
        self._limit = validate_non_negative_int(limit, "limit")
        return self

    def offset(self, offset: int) -> "SelectQuery[T]":
        self._offset = validate_non_negative_int(offset, "offset")
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
        if not isinstance(page, int) or isinstance(page, bool):
            raise TypeError(f"page must be an int, got {type(page).__name__}")
        if validate_non_negative_int(per_page, "per_page") < 1:
            raise ValueError(f"per_page must be >= 1, got {per_page}")
        page = max(page, 1)
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
        """Add an optimizer hint (MySQL 8.0+).

        The hint is written as-is inside ``/*+ ... */``, so it must come from
        trusted input. It may not contain a comment delimiter, which could end
        the comment and let the rest of the string run as SQL.
        """
        if not isinstance(hint, str):
            raise TypeError(f"Optimizer hint must be a str, got {type(hint).__name__}")
        if "*/" in hint or "/*" in hint:
            raise ValueError(
                f"Invalid optimizer hint {hint!r}: it must not contain a comment "
                "delimiter ('/*' or '*/')"
            )
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
        """Name this query for when it is used as a subquery, JOIN or CTE.

        This does not alias the table in the query's own FROM clause: use
        ``from_(table, alias)`` for that.
        """
        self._alias = validate_alias(alias)
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
                parts.append(render_func(col.name, col.args))
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
            # An explicit alias wins; otherwise use the subquery's own alias.
            # MySQL (and PostgreSQL before 16) reject a derived table without one.
            subquery_alias = self._table_alias or self._table._alias
            if not subquery_alias:
                raise ValueError(
                    "A subquery used in FROM requires an alias: call .as_() on it "
                    "or pass one to from_(subquery, alias)"
                )

            sub_sql, sub_params = self._table.build()  # type: ignore[union-attr]
            parts.append(f"({sub_sql})")
            params.extend(sub_params)
            # For subqueries, use AS keyword for alias
            parts.append(f" AS {subquery_alias}")
        else:
            parts.append(self._dialect.quote(self._table))  # type: ignore[arg-type]
            # For regular tables, alias without AS (MySQL style)
            if self._table_alias:
                parts.append(f" {self._table_alias}")

        # Index Hints
        if self._index_hint:
            hint_type, indexes = self._index_hint
            parts.append(f" {hint_type} INDEX (")
            parts.append(", ".join(map(self._dialect.quote, indexes)))
            parts.append(")")

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
        if self._offset > 0 and self._limit is None:
            raise ValueError(
                "offset() requires limit(): OFFSET without LIMIT would be ignored"
            )

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
        self._build_joins(parts, params)

        # Where
        self._build_where_having(parts, params, self._wheres, "WHERE")

        # Group By
        if self._groups:
            parts.append(" GROUP BY ")
            parts.append(", ".join(self._groups))

        # Having
        self._build_where_having(parts, params, self._havings, "HAVING")

        # Unions. An operand with its own ORDER BY / LIMIT needs parentheses
        for type_, query in self._unions:
            union_sql, union_params = query.build()
            if query._orders or query._limit is not None:
                union_sql = f"({union_sql})"
            parts.append(f" {type_} {union_sql}")
            params.extend(union_params)

        # Order By and Limit/Offset come last: with unions they apply to the
        # whole combined result
        if self._orders:
            parts.append(" ORDER BY ")
            parts.append(", ".join(self._orders))

        if self._limit is not None:
            parts.append(" ")
            parts.append(self._dialect.limit_offset(self._limit, self._offset))

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
