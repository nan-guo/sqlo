import re

# Pre-compile regex for compact operators (e.g. "age>=")
COMPACT_PATTERN = re.compile(r"^([\w\.]+)([<>=!]+)\Z")

# MySQL JSON path (without the leading "$."), e.g. "a.b[0].c", "tags[*]", "*".
# Keys that need quoting in MySQL ('$."a b"') are intentionally not supported.
_JSON_PATH_STEP = r"(?:[A-Za-z_][A-Za-z0-9_]*|\*|\[(?:\d+|\*)\])"
JSON_PATH_PATTERN = re.compile(
    rf"^(?:{_JSON_PATH_STEP})(?:\.(?:[A-Za-z_][A-Za-z0-9_]*|\*)|\[(?:\d+|\*)\])*\Z"
)

# A string JOIN condition: `column <operator> column`, joined by AND. Anything
# else (literals, functions, OR, parentheses) must be passed as Raw or Condition.
_ON_COLUMN = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*"
_ON_TERM = rf"{_ON_COLUMN}\s*(?:<=>|<=|>=|<>|!=|=|<|>)\s*{_ON_COLUMN}"
ON_PATTERN = re.compile(rf"{_ON_TERM}(?:\s+AND\s+{_ON_TERM})*", re.IGNORECASE)

# JOIN types every dialect supports; a dialect lists more in `join_types`.
PORTABLE_JOIN_TYPES = frozenset(
    {"INNER", "LEFT", "RIGHT", "CROSS", "LEFT OUTER", "RIGHT OUTER"}
)
# Types some dialects add. They are known, so using one a dialect lacks is an
# unsupported feature rather than an invalid value.
FULL_JOIN_TYPES = frozenset({"FULL", "FULL OUTER"})
