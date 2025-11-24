"""
Mixin classes for query builders to share common functionality.
"""

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from ..constants import COMPACT_PATTERN
from ..expressions import Raw

if TYPE_CHECKING:
    from ..expressions import ComplexCondition, Condition


class WhereClauseMixin:
    """Mixin for queries that support WHERE clauses."""

    _dialect: (
        Any  # Type hint for mixin - actual type defined in Query subclass
    )

    @staticmethod
    def _parse_column_operator(column: str) -> Optional[Tuple[str, str]]:
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
    ) -> Tuple[str, str, Any]:
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

        # Handle simple where: where("age >", 18) or where("age>", 18)
        if isinstance(column, str) and value is not None:
            parsed = self._parse_column_operator(column)
            if parsed:
                col_name, op = parsed
                return (
                    "AND",
                    f"{self._dialect.quote(col_name)} {op} {self._dialect.parameter_placeholder()}",
                    [value],
                )

        # Handle standard where: where("age", 18)
        if value is not None:
            return (
                "AND",
                f"{self._dialect.quote(column)} {operator} {self._dialect.parameter_placeholder()}",
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
        connector, sql, params = self._build_where_clause(
            column, value, operator
        )
        if hasattr(self, "_wheres"):
            self._wheres.append(("OR", sql, params))
        return self

    def where_in(self, column: str, values: Union[List[Any], "SelectQuery"]):
        """Add an IN WHERE condition."""
        if hasattr(values, "build"):  # Subquery
            sub_sql, sub_params = values.build()
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        "AND",
                        f"{self._dialect.quote(column)} IN ({sub_sql})",
                        sub_params,
                    )
                )
        else:
            count = len(values)
            ph = self._dialect.parameter_placeholder()
            placeholders = ", ".join([ph] * count)
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        "AND",
                        f"{self._dialect.quote(column)} IN ({placeholders})",
                        tuple(values),
                    )
                )
        return self

    def where_not_in(self, column: str, values: Union[List[Any], "SelectQuery"]):
        """Add a NOT IN WHERE condition."""
        if hasattr(values, "build"):  # Subquery
            sub_sql, sub_params = values.build()
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        "AND",
                        f"{self._dialect.quote(column)} NOT IN ({sub_sql})",
                        sub_params,
                    )
                )
        else:
            count = len(values)
            ph = self._dialect.parameter_placeholder()
            placeholders = ", ".join([ph] * count)
            if hasattr(self, "_wheres"):
                self._wheres.append(
                    (
                        "AND",
                        f"{self._dialect.quote(column)} NOT IN ({placeholders})",
                        tuple(values),
                    )
                )
        return self

    def where_null(self, column: str):
        """Add an IS NULL WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("AND", f"{self._dialect.quote(column)} IS NULL", [])
            )
        return self

    def where_not_null(self, column: str):
        """Add an IS NOT NULL WHERE condition."""
        if hasattr(self, "_wheres"):
            self._wheres.append(
                ("AND", f"{self._dialect.quote(column)} IS NOT NULL", [])
            )
        return self

    def where_between(self, column: str, value1: Any, value2: Any):
        """Add a BETWEEN WHERE condition."""
        ph = self._dialect.parameter_placeholder()
        if hasattr(self, "_wheres"):
            self._wheres.append(
                (
                    "AND",
                    f"{self._dialect.quote(column)} BETWEEN {ph} AND {ph}",
                    [value1, value2],
                )
            )
        return self

    def where_not_between(self, column: str, value1: Any, value2: Any):
        """Add a NOT BETWEEN WHERE condition."""
        ph = self._dialect.parameter_placeholder()
        if hasattr(self, "_wheres"):
            self._wheres.append(
                (
                    "AND",
                    f"{self._dialect.quote(column)} NOT BETWEEN {ph} AND {ph}",
                    [value1, value2],
                )
            )
        return self

    def where_like(self, column: str, pattern: str):
        """Add a LIKE WHERE condition."""
        return self.where(column, pattern, operator="LIKE")

    def where_not_like(self, column: str, pattern: str):
        """Add a NOT LIKE WHERE condition."""
        return self.where(column, pattern, operator="NOT LIKE")

    @staticmethod
    def _build_condition(condition) -> Tuple[str, List[Any]]:
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
