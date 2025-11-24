"""Security utilities for SQL toolkit.

This module provides functions to validate and sanitize table names, field names,
and other SQL identifiers to prevent SQL injection attacks.
"""

import re

# Pattern for valid SQL identifiers (letters, numbers, underscores, dots)
# MySQL allows backticks for identifiers, but we validate the content
VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")


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
    "validate_identifiers",
    "validate_identifier_whitelist",
    "escape_identifier",
]
