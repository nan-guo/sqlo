from typing import TYPE_CHECKING, Any, Optional, Union

from ..context import build_nested
from ..expressions import Inserted, Raw
from .base import Query

if TYPE_CHECKING:
    from .select import SelectQuery


class OnConflict:
    """What to do when an inserted row conflicts with an existing one.

    Returned by ``InsertQuery.on_conflict()``; nothing is added to the query
    until ``do_update()`` or ``do_nothing()`` is called.
    """

    def __init__(self, query: "InsertQuery", columns: tuple[str, ...]):
        self._query = query
        self._columns = columns

    def do_update(self, values: dict[str, Any]) -> "InsertQuery":
        """Update the existing row. Values are parameters, ``Raw`` or ``values_of()``."""
        if not isinstance(values, dict):
            raise TypeError(f"do_update() expects a dict, got {type(values).__name__}")
        if not values:
            raise ValueError("do_update() needs at least one column to update")
        dialect = self._query._dialect
        if dialect.conflict_target_required and not self._columns:
            raise ValueError(
                f"The {dialect.name} dialect needs the conflict columns for "
                "do_update(): on_conflict('id').do_update({...})"
            )
        self._query._conflict = (self._columns, dict(values))
        return self._query

    def do_nothing(self) -> "InsertQuery":
        """Leave the existing row as it is."""
        self._query._conflict = (self._columns, None)
        return self._query


class InsertQuery(Query):
    def __init__(self, table: str, dialect=None, debug=False):
        super().__init__(dialect, debug)
        self._table = table
        self._values: list[dict[str, Any]] = []
        self._ignore = False
        self._on_duplicate: Optional[dict[str, Any]] = None
        # (conflict columns, assignments or None for "do nothing"), see on_conflict()
        self._conflict: Optional[tuple[tuple[str, ...], Optional[dict[str, Any]]]] = None
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
        if not self._dialect.supports_insert_ignore:
            raise self._dialect.unsupported(
                "INSERT IGNORE", "Use on_conflict().do_nothing() instead."
            )
        self._ignore = True
        return self

    def on_duplicate_key_update(self, values: dict[str, Any]) -> "InsertQuery":
        if not self._dialect.supports_on_duplicate_key:
            raise self._dialect.unsupported(
                "ON DUPLICATE KEY UPDATE",
                "Use on_conflict(...).do_update(...) instead.",
            )
        if self._conflict is not None:
            raise ValueError(
                "on_duplicate_key_update() cannot be combined with on_conflict()"
            )
        self._on_duplicate = values
        return self

    def on_conflict(self, *columns: str) -> OnConflict:
        """Choose what happens when a row conflicts with an existing one.

        ``columns`` name the unique columns that conflict. PostgreSQL needs them
        for ``do_update()``; MySQL infers the unique key and ignores them::

            q.on_conflict("id").do_update({"name": values_of("name")})
            q.on_conflict("id").do_nothing()
        """
        if not self._dialect.supports_on_conflict:
            raise self._dialect.unsupported("ON CONFLICT")
        if self._on_duplicate is not None:
            raise ValueError(
                "on_conflict() cannot be combined with on_duplicate_key_update()"
            )
        for column in columns:
            self._dialect.quote(column)  # raises for an invalid identifier
        return OnConflict(self, columns)

    def _assignments(self, values: dict[str, Any], params: list[Any]) -> list[str]:
        """Render ``col = value`` strings, adding the parameters in order."""
        out = []
        for col, val in values.items():
            quoted = self._dialect.quote(col)
            if isinstance(val, Raw):
                out.append(f"{quoted} = {val.sql}")
                params.extend(val.params)
            elif isinstance(val, Inserted):
                inserted = self._dialect.quote(val.column)
                out.append(f"{quoted} = {self._dialect.inserted_value(inserted)}")
            else:
                out.append(f"{quoted} = {self._ph}")
                params.append(val)
        return out

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
            select_sql, select_params = build_nested(self._dialect, self._from_select)
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
            assignments = self._assignments(self._on_duplicate, params)
            parts.append(" ON DUPLICATE KEY UPDATE " + ", ".join(assignments))

        # ON CONFLICT: rendered by the dialect
        if self._conflict is not None:
            target_columns, updates = self._conflict
            target = [self._dialect.quote(c) for c in target_columns]
            # Qualified with the table: with INSERT ... SELECT an unqualified name is
            # ambiguous when the SELECT's table has a column of the same name
            first = (self._select_columns or list(self._values[0]))[0]
            first_sql = self._dialect.quote(f"{self._table}.{first}")
            assignments = (
                None if updates is None else self._assignments(updates, params)
            )
            parts.append(
                self._dialect.conflict_clause(target, assignments, first_sql)
            )

        sql = "".join(parts)
        params_tuple = tuple(params)
        self._print_debug(sql, params_tuple)
        return sql, params_tuple
