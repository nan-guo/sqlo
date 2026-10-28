from typing import Optional, Sequence

from ..security import MYSQL_OPERATORS
from .base import Dialect


class MySQLDialect(Dialect):
    """MySQL dialect implementation."""

    extra_operators = MYSQL_OPERATORS
    supports_insert_ignore = True
    supports_on_duplicate_key = True
    supports_on_conflict = True
    supports_dml_join = True
    supports_dml_order_limit = True

    @property
    def name(self) -> str:
        return "MySQL"

    @property
    def quote_char(self) -> str:
        return "`"

    def parameter_placeholder(self) -> str:
        return "%s"

    def index_hint(self, kind: str, quoted_indexes: str) -> str:
        return f" {kind} INDEX ({quoted_indexes})"

    def optimizer_hint(self, hints: Sequence[str]) -> str:
        return f" /*+ {' '.join(hints)} */"

    def json_extract(self, quoted_column: str, path: str) -> str:
        return f"{quoted_column}->>'$.{path}'"

    def inserted_value(self, quoted_column: str) -> str:
        return f"VALUES({quoted_column})"

    def conflict_clause(
        self,
        target: Sequence[str],
        assignments: Optional[Sequence[str]],
        first_column: str,
    ) -> str:
        # MySQL infers the conflicting unique key, so the target is not used.
        # "Do nothing" is a no-op update: unlike INSERT IGNORE it does not also
        # swallow other errors such as data truncation.
        if assignments is None:
            assignments = [f"{first_column} = {first_column}"]
        return f" ON DUPLICATE KEY UPDATE {', '.join(assignments)}"
