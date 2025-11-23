from io import StringIO
from typing import Any, Dict, List, Tuple, Union

from .base import Query


class InsertQuery(Query):
    __slots__ = ("_table", "_values", "_ignore", "_on_duplicate", "_dialect")

    def __init__(self, table: str, dialect=None):
        super().__init__(dialect)
        self._table = table
        self._values: List[Dict[str, Any]] = []
        self._ignore = False
        self._on_duplicate = None

    def values(
        self, values: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> "InsertQuery":
        if isinstance(values, dict):
            self._values.append(values)
        elif isinstance(values, list):
            self._values.extend(values)
        return self

    def ignore(self) -> "InsertQuery":
        self._ignore = True
        return self

    def on_duplicate_key_update(self, values: Dict[str, Any]) -> "InsertQuery":
        self._on_duplicate = values
        return self

    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        if not self._values:
            raise ValueError("No values to insert")

        buf = StringIO()
        columns = list(self._values[0].keys())

        # Build placeholders
        ph = self._dialect.parameter_placeholder()
        placeholders = ", ".join([ph] * len(columns))
        row_placeholder = f"({placeholders})"

        params = []
        for row in self._values:
            for col in columns:
                params.append(row.get(col))

        # Command
        buf.write("INSERT IGNORE" if self._ignore else "INSERT")
        buf.write(" INTO ")
        buf.write(self._dialect.quote(self._table))
        buf.write(" (")
        buf.write(", ".join(map(self._dialect.quote, columns)))
        buf.write(") VALUES ")
        buf.write(", ".join([row_placeholder] * len(self._values)))

        # ON DUPLICATE KEY UPDATE
        if self._on_duplicate:
            buf.write(" ON DUPLICATE KEY UPDATE ")
            first = True
            for col, val in self._on_duplicate.items():
                if not first:
                    buf.write(", ")
                first = False
                buf.write(self._dialect.quote(col))
                buf.write(" = ")
                buf.write(ph)
                params.append(val)

        return buf.getvalue(), tuple(params)
