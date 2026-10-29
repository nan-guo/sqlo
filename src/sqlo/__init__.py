"""sqlo - A modern, type-safe, and extensible SQL query builder for Python."""

from .builder import Q, QueryFactory
from .dialects.mysql import MySQLDialect
from .dialects.postgresql import PostgreSQLDialect
from .exceptions import UnsupportedFeatureError
from .expressions import JSON, Condition, Func, JSONPath, Raw, func, values_of
from .window import Window

__all__ = [
    "Q",
    "QueryFactory",
    "Raw",
    "Func",
    "func",
    "Condition",
    "JSON",
    "JSONPath",
    "Window",
    "values_of",
    "UnsupportedFeatureError",
    "MySQLDialect",
    "PostgreSQLDialect",
]

__version__ = "1.0.0"
