from abc import ABC, abstractmethod


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
        # Import here to avoid circular dependency
        from ..security import validate_identifier

        if not validate_identifier(identifier, allow_dot=True):
            raise ValueError(
                f"Invalid identifier '{identifier}'. "
                "Identifiers must contain only letters, numbers, underscores, "
                "and dots. Use Raw() for SQL functions or expressions."
            )

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
