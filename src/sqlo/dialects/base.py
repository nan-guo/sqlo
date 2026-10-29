from abc import ABC, abstractmethod
from collections.abc import Sequence
from functools import lru_cache
from typing import Optional

from ..constants import PORTABLE_JOIN_TYPES
from ..exceptions import UnsupportedFeatureError
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
    """Abstract base class for SQL dialects.

    The defaults describe the portable subset of SQL. A dialect turns features
    on by overriding the capability attributes and the hooks below; a feature
    it does not provide raises ``UnsupportedFeatureError`` instead of producing
    SQL that would fail, or mean something else, on that database.
    """

    # --- capabilities (portable defaults) ---------------------------------

    #: JOIN types the dialect supports, upper-cased (``LEFT OUTER``, ``FULL``...).
    join_types: frozenset = PORTABLE_JOIN_TYPES
    #: Comparison operators beyond ``security.PORTABLE_OPERATORS``.
    extra_operators: frozenset = frozenset()
    #: ``INSERT IGNORE``.
    supports_insert_ignore: bool = False
    #: ``ON DUPLICATE KEY UPDATE``.
    supports_on_duplicate_key: bool = False
    #: ``on_conflict()``: the portable upsert, see ``conflict_clause``.
    supports_on_conflict: bool = False
    #: Whether ``on_conflict().do_update()`` must name the conflict columns.
    conflict_target_required: bool = False
    #: JOIN in UPDATE and DELETE.
    supports_dml_join: bool = False
    #: ORDER BY and LIMIT in UPDATE and DELETE.
    supports_dml_order_limit: bool = False

    @property
    def name(self) -> str:
        """The dialect name used in error messages."""
        return type(self).__name__.removesuffix("Dialect") or "SQL"

    def unsupported(self, feature: str, hint: str = "") -> UnsupportedFeatureError:
        """The error to raise for a ``feature`` this dialect does not support."""
        return UnsupportedFeatureError(self.name, feature, hint)

    # --- hooks: return a SQL fragment, or raise for an unsupported feature --

    def index_hint(self, kind: str, quoted_indexes: str) -> str:
        """The index hint after the table, with its leading space.

        ``kind`` is ``FORCE``, ``USE`` or ``IGNORE``.
        """
        raise self.unsupported("Index hints")

    def optimizer_hint(self, hints: Sequence[str]) -> str:
        """The optimizer hint comment after ``SELECT``, with its leading space."""
        raise self.unsupported("Optimizer hints")

    def json_extract(self, quoted_column: str, path: str) -> str:
        """The expression extracting ``path`` (``a.b[0].c``) from a JSON column."""
        raise self.unsupported("JSON path extraction")

    def inserted_value(self, quoted_column: str) -> str:
        """Refer to the value an INSERT would have written to a column."""
        raise self.unsupported("Referencing the inserted value (values_of)")

    def conflict_clause(
        self,
        target: Sequence[str],
        assignments: Optional[Sequence[str]],
        first_column: str,
    ) -> str:
        """The upsert clause after the INSERT, with its leading space.

        ``target`` holds the quoted conflict columns, ``assignments`` the
        ``col = value`` strings of ``do_update`` (``None`` for ``do_nothing``),
        and ``first_column`` the first quoted inserted column.
        """
        raise self.unsupported("ON CONFLICT")

    def window_frame_bound(self, bound: str) -> str:
        """Render a validated window frame bound such as ``INTERVAL 7 DAY PRECEDING``.

        The bound arrives upper-cased with single spaces. The default leaves it
        as is.
        """
        return bound

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
