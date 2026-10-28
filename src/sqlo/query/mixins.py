"""
Mixin classes for query builders to share common functionality.
"""

from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union

from ..constants import COMPACT_PATTERN, FULL_JOIN_TYPES, ON_PATTERN, PORTABLE_JOIN_TYPES
from ..context import CompileContext
from ..expressions import ComplexCondition, Condition, JSONPath, Raw
from ..security import validate_alias, validate_operator

if TYPE_CHECKING:
    from .select import SelectQuery


def validate_join(
    dialect: Any, table: Any, join_type: str
) -> tuple[Union[str, "SelectQuery"], str]:
    """Validate and normalize the table and type of a JOIN.

    ``table`` is either ``"name"``, ``"name alias"``, ``"name AS alias"`` or a
    subquery that already has an alias. The ``ON`` condition is not handled
    here: it is raw SQL and must come from trusted input.

    :return: ``(table, join_type)``; the type is upper-cased with single spaces
    :raises ValueError: if the table reference or the join type is invalid
    """
    normalized_type = " ".join(str(join_type).upper().split())
    if normalized_type not in dialect.join_types:
        if normalized_type in PORTABLE_JOIN_TYPES | FULL_JOIN_TYPES:
            raise dialect.unsupported(f"{normalized_type} JOIN")
        raise ValueError(
            f"Invalid join type {join_type!r}. "
            f"Allowed: {', '.join(sorted(dialect.join_types))}."
        )

    if hasattr(table, "build"):  # Subquery
        if not getattr(table, "_alias", None):
            raise ValueError("A subquery used in a JOIN requires an alias (.as_())")
        return table, normalized_type

    tokens = table.split() if isinstance(table, str) else []
    if not tokens:
        raise ValueError(f"Invalid join table {table!r}")
    dialect.quote(tokens[0])  # Raises ValueError if the name is invalid
    alias = None
    if len(tokens) == 2 and tokens[1].upper() != "AS":
        alias = tokens[1]
    elif len(tokens) == 3 and tokens[1].upper() == "AS":
        alias = tokens[2]
    elif len(tokens) != 1:
        raise ValueError(
            f"Invalid join table {table!r}. "
            "Use 'name', 'name alias' or 'name AS alias'."
        )
    if alias is not None:
        validate_alias(alias)
    return " ".join(tokens), normalized_type


_Q = TypeVar("_Q", bound="WhereClauseMixin")


def render_join_on(dialect: Any, on: Any) -> tuple[str, tuple[Any, ...]]:
    """Validate a JOIN condition and render it as ``(sql, params)``.

    ``on`` may be:

    * ``None``: no ON clause;
    * a string of the form ``"a.x = b.y"``, optionally several joined by
      ``AND``. It is written as-is, which is safe because only identifiers and
      comparison operators are accepted;
    * ``Raw``: written as-is and may carry parameters, so use trusted SQL only;
    * ``Condition`` / ``ComplexCondition``: columns are validated, values are
      bound as parameters and the query's dialect is used.

    :raises ValueError: for a string that is not a column comparison, or an
        empty condition
    :raises TypeError: for any other type
    """
    if on is None:
        return "", ()
    if isinstance(on, Raw):
        return on.sql, tuple(on.params)
    if isinstance(on, (Condition, ComplexCondition)):
        ctx = CompileContext(dialect)
        sql = on.render(ctx)
        if not sql:
            raise ValueError(
                "Empty condition: it has no terms, so there is nothing to join on"
            )
        return sql, tuple(ctx.params)
    if isinstance(on, str):
        text = on.strip()
        if ON_PATTERN.fullmatch(text):
            return text, ()
        raise ValueError(
            f"Invalid join condition {on!r}. A string must be 'column <op> column' "
            "(several can be joined by AND); use Raw() or a Condition for anything "
            "else, for example functions or literal values."
        )
    raise TypeError(f"on must be a str, Raw or Condition, got {type(on).__name__}")


_J = TypeVar("_J", bound="JoinClauseMixin")


class JoinClauseMixin:
    """Mixin for queries that support JOIN clauses (SELECT, UPDATE, DELETE).

    The query class provides ``_dialect`` and the ``_joins`` list of
    ``(join_type, table, on_sql, on_params)`` tuples.
    """

    _dialect: Any
    _joins: list[tuple[str, Any, str, tuple[Any, ...]]]
    #: Set by UPDATE and DELETE, where a JOIN is a dialect capability.
    _join_feature: Optional[str] = None

    def join(
        self: _J,
        table: Union[str, "SelectQuery"],
        on: Union[str, Raw, "Condition", "ComplexCondition", None] = None,
        join_type: str = "INNER",
    ) -> _J:
        """Add a JOIN clause.

        Args:
            table: ``"name"``, ``"name alias"``, ``"name AS alias"`` or a
                subquery that has an alias.
            on: The join condition, see :func:`render_join_on`.
            join_type: ``INNER``, ``LEFT``, ``RIGHT``, ``CROSS`` or ``FULL``
                (``LEFT``, ``RIGHT`` and ``FULL`` may add ``OUTER``).
        """
        if self._join_feature and not self._dialect.supports_dml_join:
            raise self._dialect.unsupported(self._join_feature)
        table, join_type = validate_join(self._dialect, table, join_type)
        on_sql, on_params = render_join_on(self._dialect, on)
        self._joins.append((join_type, table, on_sql, on_params))
        return self

    def left_join(
        self: _J,
        table: Union[str, "SelectQuery"],
        on: Union[str, Raw, "Condition", "ComplexCondition", None] = None,
    ) -> _J:
        """Add a LEFT JOIN clause."""
        return self.join(table, on, join_type="LEFT")

    def _build_joins(self, parts: list[str], params: list[Any]) -> None:
        """Append the JOIN clauses and their parameters, in SQL order."""
        for type_, table, on_sql, on_params in self._joins:
            if hasattr(table, "build"):  # Subquery
                sub_sql, sub_params = table.build()
                parts.append(f" {type_} JOIN ({sub_sql}) AS {table._alias}")
                params.extend(sub_params)
            else:
                parts.append(f" {type_} JOIN {table}")
            if on_sql:
                parts.append(f" ON {on_sql}")
                params.extend(on_params)


class WhereClauseMixin:
    """Mixin for queries that support WHERE clauses.

    The query class provides ``_dialect``, ``_ph`` and the ``_wheres`` list of
    ``(connector, sql, params)`` tuples. Every helper returns the query itself
    and is typed so that chaining keeps the concrete query type.
    """

    _dialect: Any  # Type hint for mixin - actual type defined in Query subclass
    _ph: str
    _wheres: list[tuple[str, str, Any]]

    @staticmethod
    def _parse_column_operator(column: str) -> Optional[tuple[str, str]]:
        """Parse column and operator from string like 'age>' or 'age >'."""
        # Optimization: Fast path for space-separated operators
        if " " in column:
            parts = column.split(" ", 1)
            return parts[0], parts[1]

        # Fallback: Regex for compact operators
        match = COMPACT_PATTERN.match(column)
        if match:
            return match.group(1), match.group(2)

        return None

    def _build_where_clause(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any,
        operator: str,
    ) -> tuple[str, str, Any]:
        """
        Build a WHERE/HAVING clause from column, value, and operator.

        Returns:
            Tuple of (connector, sql, params) to append to clause list
        """
        # Handle Raw
        if isinstance(column, Raw):
            return ("AND", column.sql, column.params)

        # Handle Condition/ComplexCondition
        if isinstance(column, (Condition, ComplexCondition)):
            ctx = CompileContext(self._dialect)
            sql = column.render(ctx)
            if not sql:
                raise ValueError(
                    "Empty condition: it has no terms, so there is nothing to filter on"
                )
            return ("AND", f"({sql})", ctx.params)

        # Handle JSONPath
        if isinstance(column, JSONPath):
            col_sql = self._dialect.json_extract(
                self._dialect.quote(column.column), column.path
            )
            return (
                "AND",
                f"{col_sql} {validate_operator(operator, self._dialect)} {self._ph}",
                [value],
            )

        # Handle simple where: where("age >", 18) or where("age>", 18)
        if isinstance(column, str) and value is not None:
            parsed = self._parse_column_operator(column)
            if parsed:
                col_name, op = parsed
                return (
                    "AND",
                    f"{self._dialect.quote(col_name)} "
                    f"{validate_operator(op, self._dialect)} "
                    f"{self._ph}",
                    [value],
                )

        # Handle standard where: where("age", 18)
        if value is not None:
            return (
                "AND",
                f"{self._dialect.quote(column)} "
                f"{validate_operator(operator, self._dialect)} "
                f"{self._ph}",
                [value],
            )

        raise ValueError("Invalid where clause")

    def where(
        self: _Q,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> _Q:
        """Add a WHERE condition (joined with AND)."""
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append((connector, sql, params))
        return self

    def or_where(
        self: _Q,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ) -> _Q:
        """Add an OR WHERE condition."""
        _, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append(("OR", sql, params))
        return self

    def _where_in_internal(
        self: _Q,
        column: str,
        values: Union[list[Any], "SelectQuery"],
        connector: str = "AND",
        not_in: bool = False,
    ) -> _Q:
        operator = "NOT IN" if not_in else "IN"
        quoted = self._dialect.quote(column)  # validates, even for an empty list

        # Handle subquery
        if hasattr(values, "build"):  # Subquery
            sub_sql, sub_params = values.build()
            self._wheres.append((connector, f"{quoted} {operator} ({sub_sql})", sub_params))
        # Handle empty list edge case
        # IN () is always false, NOT IN () is always true
        elif len(values) == 0:
            self._wheres.append((connector, "TRUE" if not_in else "FALSE", []))
        else:
            placeholders = ", ".join([self._ph] * len(values))
            self._wheres.append(
                (connector, f"{quoted} {operator} ({placeholders})", tuple(values))
            )
        return self

    def where_in(self: _Q, column: str, values: Union[list[Any], "SelectQuery"]) -> _Q:
        """Add an IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=False)

    def or_where_in(
        self: _Q, column: str, values: Union[list[Any], "SelectQuery"]
    ) -> _Q:
        """Add an OR IN WHERE condition."""
        return self._where_in_internal(column, values, connector="OR", not_in=False)

    def where_not_in(
        self: _Q, column: str, values: Union[list[Any], "SelectQuery"]
    ) -> _Q:
        """Add a NOT IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=True)

    def or_where_not_in(
        self: _Q, column: str, values: Union[list[Any], "SelectQuery"]
    ) -> _Q:
        """Add an OR NOT IN WHERE condition."""
        return self._where_in_internal(column, values, connector="OR", not_in=True)

    def _where_null_internal(
        self: _Q, column: str, connector: str = "AND", not_null: bool = False
    ) -> _Q:
        operator = "IS NOT NULL" if not_null else "IS NULL"
        self._wheres.append((connector, f"{self._dialect.quote(column)} {operator}", []))
        return self

    def where_null(self: _Q, column: str) -> _Q:
        """Add an IS NULL WHERE condition."""
        return self._where_null_internal(column, connector="AND", not_null=False)

    def or_where_null(self: _Q, column: str) -> _Q:
        """Add an OR IS NULL WHERE condition."""
        return self._where_null_internal(column, connector="OR", not_null=False)

    def where_not_null(self: _Q, column: str) -> _Q:
        """Add an IS NOT NULL WHERE condition."""
        return self._where_null_internal(column, connector="AND", not_null=True)

    def or_where_not_null(self: _Q, column: str) -> _Q:
        """Add an OR IS NOT NULL WHERE condition."""
        return self._where_null_internal(column, connector="OR", not_null=True)

    def _where_between_internal(
        self: _Q,
        column: str,
        value1: Any,
        value2: Any,
        connector: str = "AND",
        not_between: bool = False,
    ) -> _Q:
        operator = "NOT BETWEEN" if not_between else "BETWEEN"
        ph = self._ph
        self._wheres.append(
            (
                connector,
                f"{self._dialect.quote(column)} {operator} {ph} AND {ph}",
                [value1, value2],
            )
        )
        return self

    def where_between(self: _Q, column: str, value1: Any, value2: Any) -> _Q:
        """Add a BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="AND", not_between=False
        )

    def or_where_between(self: _Q, column: str, value1: Any, value2: Any) -> _Q:
        """Add an OR BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="OR", not_between=False
        )

    def where_not_between(self: _Q, column: str, value1: Any, value2: Any) -> _Q:
        """Add a NOT BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="AND", not_between=True
        )

    def or_where_not_between(self: _Q, column: str, value1: Any, value2: Any) -> _Q:
        """Add an OR NOT BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="OR", not_between=True
        )

    def _where_like_internal(
        self: _Q, column: str, pattern: str, connector: str, negate: bool
    ) -> _Q:
        operator = "NOT LIKE" if negate else "LIKE"
        if pattern is None:
            raise ValueError(f"{operator} needs a pattern, got None")
        self._wheres.append(
            (connector, f"{self._dialect.quote(column)} {operator} {self._ph}", [pattern])
        )
        return self

    def where_like(self: _Q, column: str, pattern: str) -> _Q:
        """Add a LIKE WHERE condition."""
        return self._where_like_internal(column, pattern, "AND", negate=False)

    def or_where_like(self: _Q, column: str, pattern: str) -> _Q:
        """Add an OR LIKE WHERE condition."""
        return self._where_like_internal(column, pattern, "OR", negate=False)

    def where_not_like(self: _Q, column: str, pattern: str) -> _Q:
        """Add a NOT LIKE WHERE condition."""
        return self._where_like_internal(column, pattern, "AND", negate=True)

    def or_where_not_like(self: _Q, column: str, pattern: str) -> _Q:
        """Add an OR NOT LIKE WHERE condition."""
        return self._where_like_internal(column, pattern, "OR", negate=True)
