from abc import ABC, abstractmethod


class Dialect(ABC):
    """Abstract base class for SQL dialects."""

    @property
    @abstractmethod
    def quote_char(self) -> str:
        """The character used to quote identifiers."""

    def quote(self, identifier: str) -> str:
        """Quote an identifier."""
        if "." in identifier:
            parts = identifier.split(".")
            return ".".join(
                f"{self.quote_char}{part}{self.quote_char}" for part in parts
            )
        return f"{self.quote_char}{identifier}{self.quote_char}"

    @abstractmethod
    def parameter_placeholder(self) -> str:
        """The placeholder for parameters (e.g., '?' or '%s')."""

    def limit_offset(self, limit: int, offset: int) -> str:
        """Generate LIMIT and OFFSET clause."""
        if offset > 0:
            return f"LIMIT {limit} OFFSET {offset}"
        return f"LIMIT {limit}"
