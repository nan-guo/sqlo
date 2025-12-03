"""
Mixin classes for query builders to share common functionality.
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from ..constants import COMPACT_PATTERN
from ..expressions import JSONPath, Raw

if TYPE_CHECKING:
    from ..expressions import ComplexCondition, Condition
    from .select import SelectQuery


class WhereClauseMixin:
    """Mixin for queries that support WHERE clauses."""

    _dialect: Any  # Type hint for mixin - actual type defined in Query subclass
    _ph: str

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
        if hasattr(column, "parts") or hasattr(column, "left"):
            sql, params = self._build_condition(column)
            return ("AND", f"({sql})", params)

        # Handle JSONPath
        if isinstance(column, JSONPath):
            col_sql = f"{self._dialect.quote(column.column)}->>'$.{column.path}'"
            return (
                "AND",
                f"{col_sql} {operator} {self._ph}",
                [value],
            )

        # Handle simple where: where("age >", 18) or where("age>", 18)
        if isinstance(column, str) and value is not None:
            parsed = self._parse_column_operator(column)
            if parsed:
                col_name, op = parsed
                return (
                    "AND",
                    f"{self._dialect.quote(col_name)} {op} {self._ph}",
                    [value],
                )

        # Handle standard where: where("age", 18)
        if value is not None:
            return (
                "AND",
                f"{self._dialect.quote(column)} {operator} {self._ph}",
                [value],
            )

        raise ValueError("Invalid where clause")

    def or_where(
        self,
        column: Union[str, Raw, "Condition", "ComplexCondition"],
        value: Any = None,
        operator: str = "=",
    ):
        """Add an OR WHERE condition."""
        connector, sql, params = self._build_where_clause(column, value, operator)
        if hasattr(self, "_wheres"):
            self._wheres.append(("OR", sql, params))
        return self

    def _where_in_internal(
        self,
        column: str,
        values: Union[list[Any], "SelectQuery"],
        connector: str = "AND",
        not_in: bool = False,
    ):
        operator = "NOT IN" if not_in else "IN"

        # Handle subquery
        if hasattr(values, "build"):  # Subquery
            sub_sql, sub_params = values.build()
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        connector,
                        f"{self._dialect.quote(column)} {operator} ({sub_sql})",
                        sub_params,
                    )
                )
        # Handle empty list edge case
        # IN () is always false, NOT IN () is always true
        elif len(values) == 0:
            bool_value = "TRUE" if not_in else "FALSE"
            if hasattr(self, "_wheres"):
                self._wheres.append((connector, bool_value, []))
        else:
            count = len(values)
            placeholders = ", ".join([self._ph] * count)
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        connector,
                        f"{self._dialect.quote(column)} {operator} ({placeholders})",
                        tuple(values),
                    )
                )
        return self

    def where_in(self, column: str, values: Union[list[Any], "SelectQuery"]):
        """Add an IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=False)

    def or_where_in(self, column: str, values: Union[list[Any], "SelectQuery"]):
        """Add an OR IN WHERE condition."""
        return self._where_in_internal(column, values, connector="OR", not_in=False)

    def where_not_in(self, column: str, values: Union[list[Any], "SelectQuery"]):
        """Add a NOT IN WHERE condition."""
        return self._where_in_internal(column, values, connector="AND", not_in=True)

    def or_where_not_in(self, column: str, values: Union[list[Any], "SelectQuery"]):
        """Add an OR NOT IN WHERE condition."""
        return self._where_in_internal(column, values, connector="OR", not_in=True)

    def _where_null_internal(
        self, column: str, connector: str = "AND", not_null: bool = False
    ):
        operator = "IS NOT NULL" if not_null else "IS NULL"
        if hasattr(self, "_wheres"):
            self._wheres.append(
                (connector, f"{self._dialect.quote(column)} {operator}", [])
            )
        return self

    def where_null(self, column: str):
        """Add an IS NULL WHERE condition."""
        return self._where_null_internal(column, connector="AND", not_null=False)

    def or_where_null(self, column: str):
        """Add an OR IS NULL WHERE condition."""
        return self._where_null_internal(column, connector="OR", not_null=False)

    def where_not_null(self, column: str):
        """Add an IS NOT NULL WHERE condition."""
        return self._where_null_internal(column, connector="AND", not_null=True)

    def or_where_not_null(self, column: str):
        """Add an OR IS NOT NULL WHERE condition."""
        return self._where_null_internal(column, connector="OR", not_null=True)

    def _where_between_internal(
        self,
        column: str,
        value1: Any,
        value2: Any,
        connector: str = "AND",
        not_between: bool = False,
    ):
        operator = "NOT BETWEEN" if not_between else "BETWEEN"
        ph = self._ph
        if hasattr(self, "_wheres"):
            self._wheres.append(
                (
                    connector,
                    f"{self._dialect.quote(column)} {operator} {ph} AND {ph}",
                    [value1, value2],
                )
            )
        return self

    def where_between(self, column: str, value1: Any, value2: Any):
        """Add a BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="AND", not_between=False
        )

    def or_where_between(self, column: str, value1: Any, value2: Any):
        """Add an OR BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="OR", not_between=False
        )

    def where_not_between(self, column: str, value1: Any, value2: Any):
        """Add a NOT BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="AND", not_between=True
        )

    def or_where_not_between(self, column: str, value1: Any, value2: Any):
        """Add an OR NOT BETWEEN WHERE condition."""
        return self._where_between_internal(
            column, value1, value2, connector="OR", not_between=True
        )

    def where_like(self, column: str, pattern: str):
        """Add a LIKE WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("AND", f"{self._dialect.quote(column)} LIKE {self._ph}", [pattern])
            )
        return self

    def or_where_like(self, column: str, pattern: str):
        """Add an OR LIKE WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("OR", f"{self._dialect.quote(column)} LIKE {self._ph}", [pattern])
            )
        return self

    def where_not_like(self, column: str, pattern: str):
        """Add a NOT LIKE WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("AND", f"{self._dialect.quote(column)} NOT LIKE {self._ph}", [pattern])
            )
        return self

    def or_where_not_like(self, column: str, pattern: str):
        """Add an OR NOT LIKE WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("OR", f"{self._dialect.quote(column)} NOT LIKE {self._ph}", [pattern])
            )
        return self

    @staticmethod
    def _build_condition(condition) -> tuple[str, list[Any]]:
        """
        Recursively build SQL from Condition or ComplexCondition objects.

        Args:
            condition: Condition or ComplexCondition object

        Returns:
            Tuple of (sql, params)
        """
        # Handle Condition (has parts)
        if hasattr(condition, "parts"):
            parts_sql = []
            params = []
            for sql, p in condition.parts:
                if sql in ("AND", "OR"):
                    parts_sql.append(sql)
                else:
                    parts_sql.append(sql)
                    if p:
                        params.extend(p)
            sql = " ".join(parts_sql)
            if len(condition.parts) > 1:
                return f"({sql})", params
            return sql, params

        # Handle ComplexCondition (has left/right)
        if hasattr(condition, "left"):
            left_sql, left_params = WhereClauseMixin._build_condition(condition.left)
            right_sql, right_params = WhereClauseMixin._build_condition(condition.right)
            return (
                f"({left_sql} {condition.operator} {right_sql})",
                left_params + right_params,
            )

        return "", []
