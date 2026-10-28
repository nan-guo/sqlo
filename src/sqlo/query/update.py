from collections import Counter
from typing import Any, Optional, Union

from ..expressions import ComplexCondition, Condition, Raw
from ..security import validate_non_negative_int
from .base import Query
from .mixins import WhereClauseMixin, validate_join


class UpdateQuery(WhereClauseMixin, Query):
    __slots__ = (
        "_table",
        "_values",
        "_wheres",
        "_limit",
        "_order_bys",
        "_joins",
        "_dialect",
        "_allow_all_rows",
    )

    def __init__(self, table: str, dialect=None, debug=False):
        super().__init__(dialect, debug)
        self._table = table
        self._values: dict[str, Any] = {}
        self._wheres: list[tuple[str, str, Any]] = []
        self._limit: Optional[int] = None
        self._order_bys: list[str] = []
        self._joins: list[tuple[str, str, Optional[str]]] = []  # (type, table, on)
        self._allow_all_rows: bool = False

    def set(self, values: dict[str, Any]) -> "UpdateQuery":
        self._values.update(values)
        return self

    def join(
        self, table: str, on: Optional[str] = None, join_type: str = "INNER"
    ) -> "UpdateQuery":
        """Add a JOIN clause (MySQL multi-table UPDATE)."""
        table, join_type = validate_join(self._dialect, table, join_type)
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
        connector, sql, params = self._build_where_clause(column, value, operator)
        self._wheres.append((connector, sql, params))
        return self

    def limit(self, limit: int) -> "UpdateQuery":
        self._limit = validate_non_negative_int(limit, "limit")
        return self

    def order_by(self, *columns: str) -> "UpdateQuery":
        for col in columns:
            direction = "ASC"
            if col.startswith("-"):
                direction = "DESC"
                col = col[1:]
            self._order_bys.append(f"{self._dialect.quote(col)} {direction}")
        return self

    def allow_all_rows(self) -> "UpdateQuery":
        """Allow UPDATE without WHERE clause (updates all rows).

        This is a safety feature to prevent accidental mass updates.
        You must call this method explicitly if you want to update all rows.

        Returns:
            Self for method chaining

        Example:
            >>> Q.update("users").set({"active": False}).allow_all_rows().build()
        """
        self._allow_all_rows = True
        return self

    def batch_update(self, values: list[dict[str, Any]], key: str) -> "UpdateQuery":
        """
        Perform a batch update using CASE WHEN.

        Args:
            values: List of dictionaries containing values to update.
                    Every dictionary must have the same columns, including
                    the key column, and key values must be unique.
                    An empty list does nothing.
            key: The column name to use as the key (e.g., "id").

        Raises:
            TypeError: If a row is not a dictionary.
            ValueError: If the key is missing, the rows have different
                columns, or a key value appears more than once.
        """
        if not values:
            return self

        for i, row in enumerate(values):
            if not isinstance(row, dict):
                raise TypeError(f"Row {i} must be a dict, got {type(row).__name__}")

        first_keys = values[0].keys()
        if key not in first_keys:
            raise ValueError(f"Key '{key}' not found in values")

        # A missing column would raise KeyError and an extra one would be lost
        for i, row in enumerate(values):
            if row.keys() != first_keys:
                raise ValueError(
                    f"Row {i} has columns {list(row)} but expected "
                    f"{list(first_keys)}: all rows must have the same columns"
                )

        # With a repeated key the CASE is ambiguous: only the first WHEN applies
        ids = [row[key] for row in values]
        duplicates = [k for k, n in Counter(ids).items() if n > 1]
        if duplicates:
            raise ValueError(
                f"Duplicate values for key '{key}': {duplicates[:5]}"
            )

        # Group values by column
        columns_to_update = [k for k in first_keys if k != key]

        for col in columns_to_update:
            # Build CASE WHEN
            case_parts = [f"CASE {self._dialect.quote(key)}"]
            case_params = []

            for row in values:
                case_parts.append(f"WHEN {self._ph} THEN {self._ph}")
                case_params.extend([row[key], row[col]])

            case_parts.append("END")

            # Set column to Raw SQL
            self.set({col: Raw(" ".join(case_parts), case_params)})

        # Add WHERE IN clause
        self.where_in(key, ids)

        return self

    def build(self) -> tuple[str, tuple[Any, ...]]:
        if not self._table:
            raise ValueError("No table specified")
        if not self._values:
            raise ValueError("No values to update")

        # Safety check: UPDATE without WHERE
        if not self._wheres and not self._allow_all_rows:
            raise ValueError(
                "UPDATE without WHERE clause would affect all rows. "
                "If this is intentional, call .allow_all_rows() first."
            )

        parts: list[str] = []
        params: list[Any] = []
        ph = self._ph

        # CTEs
        self._build_ctes(parts, params)

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
        if self._limit is not None:
            parts.append(f" LIMIT {self._limit}")

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
