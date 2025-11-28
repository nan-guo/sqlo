import re

# Pre-compile regex for compact operators (e.g. "age>=")
COMPACT_PATTERN = re.compile(r"^([\w\.]+)([<>=!]+)$")
