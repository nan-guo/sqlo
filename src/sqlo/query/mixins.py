"""
Mixin classes for query builders to share common functionality.
"""

from typing import Any, List, Tuple, Union

from ..expressions import Raw


class WhereClauseMixin:
    """Mixin for queries that support WHERE clauses."""

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

        # Handle simple where: where("age >", 18)
        if " " in column and value is not None:
            parts = column.split(" ", 1)
            col_name = parts[0]
            op = parts[1]
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

    def _build_condition(self, condition) -> Tuple[str, List[Any]]:
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
            left_sql, left_params = self._build_condition(condition.left)
            right_sql, right_params = self._build_condition(condition.right)
            return (
                f"({left_sql} {condition.operator} {right_sql})",
                left_params + right_params,
            )

        return "", []
