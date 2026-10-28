import re

from ..constants import FULL_JOIN_TYPES, PORTABLE_JOIN_TYPES
from ..security import POSTGRESQL_OPERATORS
from .base import Dialect

_JSON_STEP = re.compile(r"\[\*\]|\[\d+\]|\*|[A-Za-z_][A-Za-z0-9_]*")
_INTERVAL_BOUND = re.compile(r"^INTERVAL (\d+) ([A-Z]+) (PRECEDING|FOLLOWING)$")


class PostgreSQLDialect(Dialect):
    """PostgreSQL dialect (the ``%s`` placeholder of psycopg).

    UPDATE and DELETE with JOIN, ORDER BY or LIMIT, INSERT IGNORE, ON DUPLICATE
    KEY UPDATE and MySQL's index and optimizer hints do not exist in
    PostgreSQL, so they raise ``UnsupportedFeatureError``.
    """

    join_types = PORTABLE_JOIN_TYPES | FULL_JOIN_TYPES
    extra_operators = POSTGRESQL_OPERATORS

    @property
    def name(self) -> str:
        return "PostgreSQL"

    @property
    def quote_char(self) -> str:
        return '"'

    def parameter_placeholder(self) -> str:
        return "%s"

    def json_extract(self, quoted_column: str, path: str) -> str:
        """``col ->> 'key'``, ``col ->> 0`` or ``col #>> '{a,b,0}'``.

        The path was validated when the ``JSONPath`` was created, so its steps
        are plain keys and numbers. MySQL's ``'$.a.b'`` form must never be
        emitted: PostgreSQL accepts it and silently returns NULL.
        """
        steps = []
        for token in _JSON_STEP.findall(path):
            if token in ("*", "[*]"):
                raise self.unsupported(
                    "JSON wildcard paths", "Use Raw() for a custom expression."
                )
            steps.append(token[1:-1] if token.startswith("[") else token)
        if len(steps) == 1:
            step = steps[0]
            return f"{quoted_column} ->> {step if step.isdigit() else repr(step)}"
        return f"{quoted_column} #>> '{{{','.join(steps)}}}'"

    def window_frame_bound(self, bound: str) -> str:
        """``INTERVAL 7 DAY PRECEDING`` becomes ``INTERVAL '7 day' PRECEDING``.

        PostgreSQL has no QUARTER unit, so ``n`` quarters are ``3n`` months.
        """
        match = _INTERVAL_BOUND.match(bound)
        if not match:
            return bound
        amount, unit, direction = match.groups()
        if unit == "QUARTER":
            amount, unit = str(int(amount) * 3), "MONTH"
        return f"INTERVAL '{amount} {unit.lower()}' {direction}"

