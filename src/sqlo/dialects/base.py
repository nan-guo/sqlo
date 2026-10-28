from abc import ABC, abstractmethod
from functools import lru_cache

from ..security import require_identifier


@lru_cache(maxsize=4096)
def _quote_identifier(quote_char: str, identifier: str) -> str:
    """Validate and quote an identifier; results are cached.

    Identifiers repeat across queries, and validating plus quoting one costs
    about as much as the rest of building a simple query. The cache is bounded
    because identifiers may come from dynamic input, and invalid identifiers
    raise, so they are never stored.
    """
    require_identifier(identifier)
    if "." in identifier:
        parts = identifier.split(".")
        return ".".join(f"{quote_char}{part}{quote_char}" for part in parts)
    return f"{quote_char}{identifier}{quote_char}"


class Dialect(ABC):
    """Abstract base class for SQL dialects."""

    @property
    @abstractmethod
    def quote_char(self) -> str:
        """The character used to quote identifiers."""

    def quote(self, identifier: str) -> str:
        """Quote an identifier with mandatory validation.

        Args:
            identifier: The identifier to quote (table name, column name, etc.)

        Returns:
            Quoted identifier

        Raises:
            ValueError: If identifier contains invalid characters
        """
        if not isinstance(identifier, str):
            require_identifier(identifier)  # raises ValueError for non-strings
        return _quote_identifier(self.quote_char, identifier)

    @abstractmethod
    def parameter_placeholder(self) -> str:
        """The placeholder for parameters (e.g., '?' or '%s')."""

    def placeholder(self, index: int) -> str:
        """The placeholder for the ``index``-th (1-based) parameter of a statement.

        Only position-independent placeholders (``%s``, ``?``) are supported:
        queries render each clause on its own, so ``index`` is not a statement
        wide position. The default ignores it.
        """
        return self.parameter_placeholder()

    def limit_offset(self, limit: int, offset: int) -> str:
        """Generate LIMIT and OFFSET clause."""
        if offset > 0:
            return f"LIMIT {limit} OFFSET {offset}"
        return f"LIMIT {limit}"
