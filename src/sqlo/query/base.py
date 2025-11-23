from abc import ABC, abstractmethod
from typing import Any, Tuple

from ..dialects.base import Dialect
from ..dialects.mysql import MySQLDialect


class Query(ABC):
    """Abstract base class for all queries."""

    def __init__(self, dialect: Dialect = None):
        self._dialect = dialect or MySQLDialect()

    @abstractmethod
    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        """Build the query and return (sql, params)."""
        raise NotImplementedError("Subclasses must implement build()")

    def __str__(self) -> str:
        """Return the compiled SQL string (for debugging)."""
        sql, _ = self.build()
        return sql
