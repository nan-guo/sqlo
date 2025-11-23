# sqlo

**sqlo** is a modern, type-safe, and extensible SQL query builder for Python. It allows you to construct complex SQL queries using a fluent, Pythonic API while ensuring safety against SQL injection.

## Features

- 🛡️ **Safe**: Automatic parameter binding prevents SQL injection.
- 🐍 **Pythonic**: Fluent API design that feels natural to Python developers.
- 🧩 **Composable**: Build complex queries from reusable parts.
- 🚀 **Extensible**: Support for custom dialects and functions.
- 🔍 **Type-Safe**: Designed with type hints for better IDE support.

## Installation

```bash
pip install sqlo
```

## Quick Start

```python
from sqlo import Q

# SELECT query
query = Q.select("id", "name").from_("users").where("active", True)
sql, params = query.build()
# SQL: SELECT `id`, `name` FROM `users` WHERE `active` = ?
# Params: (True,)

# INSERT query
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"}
])
sql, params = query.build()
```

## Documentation

Full documentation is available in the [docs](docs/) directory.

- [Getting Started](docs/getting-started.md)
- [SELECT Queries](docs/select.md)
- [INSERT Queries](docs/insert.md)
- [UPDATE Queries](docs/update.md)
- [DELETE Queries](docs/delete.md)
- [JOIN Operations](docs/joins.md)
- [Condition Objects](docs/conditions.md)
- [Expressions & Functions](docs/expressions.md)

## License

MIT License
