"""Compile context shared by expression nodes while they render to SQL."""

from typing import Any, Optional

from .dialects.base import Dialect


class CompileContext:
    """Collects the parameters of a statement while its nodes render.

    Nodes are dialect-independent data. They render through a context, which
    supplies identifier quoting and placeholders from a dialect and keeps the
    SQL text and the parameter list in the same order.
    """

    __slots__ = ("dialect", "params")

    def __init__(self, dialect: Optional[Dialect] = None):
        if dialect is None:
            from .builder import Q

            dialect = Q.get_dialect()
        self.dialect = dialect
        self.params: list[Any] = []

    def quote(self, identifier: str) -> str:
        """Validate and quote an identifier with the dialect."""
        return self.dialect.quote(identifier)

    def param(self, value: Any) -> str:
        """Record a parameter and return its placeholder."""
        self.params.append(value)
        return self.dialect.placeholder(len(self.params))

    def subquery(self, query: Any) -> str:
        """Build a nested query and merge its parameters.

        The nested query must use the same dialect as this context.
        """
        sub_dialect = getattr(query, "_dialect", None)
        if sub_dialect is not None and type(sub_dialect) is not type(self.dialect):
            raise ValueError(
                f"Subquery dialect {type(sub_dialect).__name__} does not match "
                f"{type(self.dialect).__name__}"
            )
        sql, params = query.build()
        self.params.extend(params)
        return sql
