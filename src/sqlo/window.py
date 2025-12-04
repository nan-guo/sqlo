"""Window function support for sqlo."""

from typing import Any, Optional


class Window:
    """
    Represents a SQL window specification for window functions.

    Example:
        >>> Window.partition_by("department").order_by("-salary")
        >>> Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
    """

    def __init__(self) -> None:
        self._partition_by_cols: list[str] = []
        self._order_by_cols: list[str] = []
        self._frame_clause: Optional[str] = None

    @classmethod
    def partition_by(cls, *columns: str) -> "Window":
        """Create a window with PARTITION BY clause."""
        window = cls()
        window._partition_by_cols = list(columns)
        return window

    @classmethod
    def order_by(cls, *columns: str) -> "Window":
        """Create a window with ORDER BY clause."""
        window = cls()
        window._order_by_cols = list(columns)
        return window

    def and_partition_by(self, *columns: str) -> "Window":
        """Add PARTITION BY clause to the window."""
        self._partition_by_cols.extend(columns)
        return self

    def and_order_by(self, *columns: str) -> "Window":
        """Add ORDER BY clause to the window."""
        self._order_by_cols.extend(columns)
        return self

    def rows_between(self, start: str, end: str) -> "Window":
        """
        Add ROWS BETWEEN frame clause.

        Args:
            start: Start of the frame (e.g., "UNBOUNDED PRECEDING", "1 PRECEDING", "CURRENT ROW")
            end: End of the frame (e.g., "CURRENT ROW", "1 FOLLOWING", "UNBOUNDED FOLLOWING")
        """
        self._frame_clause = f"ROWS BETWEEN {start} AND {end}"
        return self

    def range_between(self, start: str, end: str) -> "Window":
        """
        Add RANGE BETWEEN frame clause.

        Args:
            start: Start of the frame
            end: End of the frame
        """
        self._frame_clause = f"RANGE BETWEEN {start} AND {end}"
        return self

    def build(self, dialect: Any) -> str:
        """Build the window specification SQL."""
        parts = []

        # PARTITION BY
        if self._partition_by_cols:
            quoted_cols = [dialect.quote(col) for col in self._partition_by_cols]
            parts.append(f"PARTITION BY {', '.join(quoted_cols)}")

        # ORDER BY
        if self._order_by_cols:
            order_parts = []
            for col in self._order_by_cols:
                if col.startswith("-"):
                    order_parts.append(f"{dialect.quote(col[1:])} DESC")
                else:
                    order_parts.append(f"{dialect.quote(col)} ASC")
            parts.append(f"ORDER BY {', '.join(order_parts)}")

        # Frame clause
        if self._frame_clause:
            parts.append(self._frame_clause)

        return " ".join(parts)


class WindowFunc:
    """
    Represents a window function with OVER clause.

    This is created when calling .over() on a Func object.
    """

    def __init__(
        self, func_name: str, func_args: tuple, window: Optional[Window] = None
    ) -> None:
        self.func_name = func_name
        self.func_args = func_args
        self.window = window
        self.alias: Optional[str] = None

    def as_(self, alias: str) -> "WindowFunc":
        """Set an alias for the window function."""
        self.alias = alias
        return self

    def build(self, dialect: Any) -> str:
        """Build the window function SQL."""
        # Build function call
        if self.func_args:
            args_str = ", ".join(str(arg) for arg in self.func_args)
            func_sql = f"{self.func_name}({args_str})"
        else:
            func_sql = f"{self.func_name}()"

        # Build OVER clause
        if self.window:
            window_sql = self.window.build(dialect)
            return f"{func_sql} OVER ({window_sql})"
        else:
            return f"{func_sql} OVER ()"
