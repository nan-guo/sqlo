"""Compile context shared by expression nodes while they render to SQL."""

from typing import Any, Optional

from .dialects.base import Dialect


def _name(dialect: Any) -> str:
    return getattr(dialect, "name", type(dialect).__name__)


def build_nested(dialect: Dialect, query: Any) -> tuple[str, tuple[Any, ...]]:
    """Build a query nested in another one, which must use the same dialect.

    A subquery rendered by another dialect would bring its own quoting and
    syntax into the statement, so it is rejected.
    """
    nested = getattr(query, "_dialect", None)
    if nested is not None and not (
        isinstance(nested, type(dialect)) or isinstance(dialect, type(nested))
    ):
        raise ValueError(
            f"A subquery built for the {_name(nested)} dialect cannot be used in "
            f"a query built for the {_name(dialect)} dialect"
        )
    return query.build()


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
        sql, params = build_nested(self.dialect, query)
        self.params.extend(params)
        return sql
