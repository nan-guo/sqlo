import re

# Pre-compile regex for compact operators (e.g. "age>=")
COMPACT_PATTERN = re.compile(r"^([\w\.]+)([<>=!]+)$")

# MySQL JSON path (without the leading "$."), e.g. "a.b[0].c", "tags[*]", "*".
# Keys that need quoting in MySQL ('$."a b"') are intentionally not supported.
_JSON_PATH_STEP = r"(?:[A-Za-z_][A-Za-z0-9_]*|\*|\[(?:\d+|\*)\])"
JSON_PATH_PATTERN = re.compile(
    rf"^(?:{_JSON_PATH_STEP})(?:\.(?:[A-Za-z_][A-Za-z0-9_]*|\*)|\[(?:\d+|\*)\])*$"
)
