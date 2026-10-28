from typing import TYPE_CHECKING, Any, Optional, Union

from ..expressions import Raw
from .base import Query

if TYPE_CHECKING:
    from .select import SelectQuery


class InsertQuery(Query):
    __slots__ = (
        "_table",
        "_values",
        "_ignore",
        "_on_duplicate",
        "_from_select",
        "_select_columns",
        "_dialect",
    )

    def __init__(self, table: str, dialect=None, debug=False):
        super().__init__(dialect, debug)
        self._table = table
        self._values: list[dict[str, Any]] = []
        self._ignore = False
        self._on_duplicate: Optional[dict[str, Any]] = None
        self._from_select: Optional[SelectQuery] = None
        self._select_columns: Optional[list[str]] = None

    def values(
        self, values: Union[dict[str, Any], list[dict[str, Any]]]
    ) -> "InsertQuery":
        if isinstance(values, dict):
            rows = [values]
        elif isinstance(values, list):
            rows = values
        else:
            raise TypeError(
                "values() expects a dict or a list of dicts, "
                f"got {type(values).__name__}"
            )

        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise TypeError(f"Row {i} must be a dict, got {type(row).__name__}")

        # Every row must have the same columns as the first row, otherwise
        # a missing column would become NULL and an extra one would be lost
        if rows:
            expected = (self._values[0] if self._values else rows[0]).keys()
            for i, row in enumerate(rows):
                if row.keys() != expected:
                    raise ValueError(
                        f"Row {i} has columns {list(row)} but expected "
                        f"{list(expected)}: all rows must have the same columns"
                    )

        self._values.extend(rows)
        return self

    def ignore(self) -> "InsertQuery":
        self._ignore = True
        return self

    def on_duplicate_key_update(self, values: dict[str, Any]) -> "InsertQuery":
        self._on_duplicate = values
        return self

    def from_select(
        self, columns: list[str], select_query: "SelectQuery"
    ) -> "InsertQuery":
        """Insert data from a SELECT query."""
        self._select_columns = columns
        self._from_select = select_query
        return self

    def build(self) -> tuple[str, tuple[Any, ...]]:
        parts: list[str] = []
        params: list[Any] = []
        ph = self._ph

        # CTEs
        self._build_ctes(parts, params)

        # Command
        parts.append("INSERT IGNORE" if self._ignore else "INSERT")
        parts.append(" INTO ")
        parts.append(self._dialect.quote(self._table))

        # Handle INSERT ... SELECT
        if self._from_select:
            if not self._select_columns:
                raise ValueError("Columns must be specified for INSERT ... SELECT")
            parts.append(" (")
            parts.append(", ".join(map(self._dialect.quote, self._select_columns)))
            parts.append(") ")

            # Build SELECT query
            select_sql, select_params = self._from_select.build()
            parts.append(select_sql)
            params.extend(select_params)
        else:
            # Handle INSERT ... VALUES
            if not self._values:
                raise ValueError("No values to insert")

            columns = list(self._values[0].keys())

            # Build placeholders
            placeholders = ", ".join([ph] * len(columns))
            row_placeholder = f"({placeholders})"

            for row in self._values:
                for col in columns:
                    params.append(row[col])

            parts.append(" (")
            parts.append(", ".join(map(self._dialect.quote, columns)))
            parts.append(") VALUES ")
            parts.append(", ".join([row_placeholder] * len(self._values)))

        # ON DUPLICATE KEY UPDATE
        if self._on_duplicate:
            parts.append(" ON DUPLICATE KEY UPDATE ")
            first = True
            for col, val in self._on_duplicate.items():
                if not first:
                    parts.append(", ")
                first = False
                parts.append(self._dialect.quote(col))
                parts.append(" = ")

                # Handle Raw expressions
                if isinstance(val, Raw):
                    parts.append(val.sql)
                    params.extend(val.params)
                # Handle regular values
                else:
                    parts.append(ph)
                    params.append(val)

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
