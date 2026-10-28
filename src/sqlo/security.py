"""Security utilities for SQL toolkit.

This module provides functions to validate and sanitize table names, field names,
and other SQL identifiers to prevent SQL injection attacks.
"""

import re
from typing import Any

from .exceptions import UnsupportedFeatureError

# Pattern for valid SQL identifiers (letters, numbers, underscores, dots)
# MySQL allows backticks for identifiers, but we validate the content.
# Dots separate non-empty segments ("a.b", never "a..b" or "a."). \Z anchors
# the end: "$" would also accept a trailing newline.
VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*\Z")


def validate_identifier(identifier: str, allow_dot: bool = True) -> bool:
    """Validate a SQL identifier (table name, field name, etc.).

    This function checks if an identifier contains only safe characters:
    - Letters (a-z, A-Z)
    - Numbers (0-9)
    - Underscores (_)
    - Dots (.) if allow_dot is True (for table.field notation)

    :param identifier: The identifier to validate
    :param allow_dot: Whether to allow dots in the identifier (default: True)
    :return: True if the identifier is valid, False otherwise

    :Example:

    >>> validate_identifier("users")
    True
    >>> validate_identifier("user_id")
    True
    >>> validate_identifier("users.id")
    True
    >>> validate_identifier("users; DROP TABLE users; --")
    False
    >>> validate_identifier("123invalid")
    False
    """
    if not identifier or not isinstance(identifier, str):
        return False

    if not allow_dot and "." in identifier:
        return False

    return bool(VALID_IDENTIFIER_PATTERN.match(identifier))


def validate_alias(alias: str) -> str:
    """Validate a table or subquery alias (a plain identifier, no dots).

    Aliases are interpolated into SQL, so they must be simple identifiers.

    :raises ValueError: if the alias is not a valid identifier
    """
    if not validate_identifier(alias, allow_dot=False):
        raise ValueError(
            f"Invalid alias {alias!r}. "
            "Aliases must start with a letter or underscore and contain only "
            "letters, numbers and underscores."
        )
    return alias


# Operators every dialect supports.
PORTABLE_OPERATORS = frozenset(
    {
        "=",
        "!=",
        "<>",
        "<",
        "<=",
        ">",
        ">=",
        "LIKE",
        "NOT LIKE",
        "IN",
        "NOT IN",
        "IS",
        "IS NOT",
        "IS NULL",
        "IS NOT NULL",
    }
)
# Operators only some dialects have. A dialect lists its own in `extra_operators`.
MYSQL_OPERATORS = frozenset({"<=>", "REGEXP", "NOT REGEXP"})
POSTGRESQL_OPERATORS = frozenset(
    {
        "~",
        "~*",
        "!~",
        "!~*",
        "ILIKE",
        "NOT ILIKE",
        "IS DISTINCT FROM",
        "IS NOT DISTINCT FROM",
    }
)
# Every operator sqlo knows. A `Condition` is built before the dialect is known,
# so it is checked against this set, and again against the dialect when rendered.
ALLOWED_OPERATORS = PORTABLE_OPERATORS | MYSQL_OPERATORS | POSTGRESQL_OPERATORS


def check_operator_for_dialect(dialect: Any, operator: str) -> None:
    """Raise if a normalized ``operator`` is not supported by ``dialect``.

    :raises UnsupportedFeatureError: if the dialect does not have the operator
    """
    if operator not in PORTABLE_OPERATORS and operator not in dialect.extra_operators:
        raise UnsupportedFeatureError(dialect.name, f"The {operator} operator")


def validate_operator(operator: str, dialect: Any = None) -> str:
    """Validate a comparison operator against the allowed set.

    Operators are interpolated directly into SQL, so anything outside
    ``ALLOWED_OPERATORS`` is rejected. Matching is case-insensitive and
    ignores repeated whitespace. With a ``dialect``, the operator must also be
    supported by it.

    :return: The operator normalized to upper case with single spaces
    :raises ValueError: if the operator is not allowed
    :raises UnsupportedFeatureError: if the dialect does not have the operator
    """
    if isinstance(operator, str):
        normalized = " ".join(operator.upper().split())
        if normalized in ALLOWED_OPERATORS:
            if dialect is not None and normalized not in PORTABLE_OPERATORS:
                check_operator_for_dialect(dialect, normalized)
            return normalized
    raise ValueError(
        f"Invalid operator {operator!r}. "
        f"Allowed operators: {', '.join(sorted(ALLOWED_OPERATORS))}. "
        "Use Raw() for other expressions."
    )


def validate_non_negative_int(value: object, name: str) -> int:
    """Ensure ``value`` is a non-negative ``int`` (``bool`` is rejected).

    Used for values interpolated directly into SQL, such as LIMIT and OFFSET.

    :raises TypeError: if ``value`` is not an ``int``
    :raises ValueError: if ``value`` is negative
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def require_identifier(identifier: str) -> str:
    """Return ``identifier`` if it is a valid SQL identifier, else raise.

    :raises ValueError: if the identifier contains invalid characters
    """
    if not validate_identifier(identifier, allow_dot=True):
        raise ValueError(
            f"Invalid identifier '{identifier}'. "
            "Identifiers must contain only letters, numbers, underscores, "
            "and dots. Use Raw() for SQL functions or expressions."
        )
    return identifier


def validate_identifiers(identifiers: list[str], allow_dot: bool = True) -> bool:
    """Validate multiple SQL identifiers.

    :param identifiers: List of identifiers to validate
    :param allow_dot: Whether to allow dots in identifiers (default: True)
    :return: True if all identifiers are valid, False otherwise

    :Example:

    >>> validate_identifiers(["users", "orders", "user_id"])
    True
    >>> validate_identifiers(["users", "orders; DROP TABLE users; --"])
    False
    """
    return all(validate_identifier(identifier, allow_dot) for identifier in identifiers)


def validate_identifier_whitelist(
    identifier: str, whitelist: set[str], case_sensitive: bool = True
) -> bool:
    """Validate an identifier against a whitelist.

    This is the safest approach: only allow identifiers that are explicitly
    in a predefined whitelist.

    :param identifier: The identifier to validate
    :param whitelist: Set of allowed identifiers
    :param case_sensitive: Whether the comparison should be case-sensitive (default: True)
    :return: True if the identifier is in the whitelist, False otherwise

    :Example:

    >>> allowed_tables = {"users", "orders", "products"}
    >>> validate_identifier_whitelist("users", allowed_tables)
    True
    >>> validate_identifier_whitelist("Users", allowed_tables)
    False
    >>> validate_identifier_whitelist("users", allowed_tables, case_sensitive=False)
    True
    >>> validate_identifier_whitelist("malicious_table", allowed_tables)
    False
    """
    if not identifier or not isinstance(identifier, str):
        return False

    if case_sensitive:
        return identifier in whitelist
    else:
        return identifier.lower() in {name.lower() for name in whitelist}


def escape_identifier(identifier: str, quote_char: str = "`") -> str:
    """Escape a SQL identifier with quotes.

    Note: This function only adds quotes around the identifier. It does NOT
    escape special characters inside the identifier. You should still validate
    the identifier before using this function.

    :param identifier: The identifier to escape
    :param quote_char: The quote character to use (default: backtick for MySQL)
    :return: The escaped identifier

    :Example:

    >>> escape_identifier("users")
    '`users`'
    >>> escape_identifier("user.id")
    '`user.id`'
    """
    if not identifier:
        return identifier

    # Split by dot for table.field notation
    parts = identifier.split(".")
    escaped_parts = [f"{quote_char}{part}{quote_char}" for part in parts]
    return ".".join(escaped_parts)


__all__ = [
    "validate_identifier",
    "require_identifier",
    "validate_identifiers",
    "validate_identifier_whitelist",
    "validate_non_negative_int",
    "validate_operator",
    "check_operator_for_dialect",
    "PORTABLE_OPERATORS",
    "MYSQL_OPERATORS",
    "POSTGRESQL_OPERATORS",
    "validate_alias",
    "ALLOWED_OPERATORS",
    "escape_identifier",
]
