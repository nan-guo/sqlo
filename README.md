# sqlo

[![CI](https://github.com/nan-guo/sqlo/actions/workflows/ci.yml/badge.svg)](https://github.com/nan-guo/sqlo/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlo)](https://pypi.org/project/sqlo/)
[![Documentation](https://img.shields.io/badge/docs-github%20pages-blue)](https://nan-guo.github.io/sqlo/)
[![License](https://img.shields.io/github/license/nan-guo/sqlo)](LICENSE)

A **lightweight** and **simple** SQL query builder for Python. Build SQL queries with a clean, intuitive API while staying safe from SQL injection.

## Why sqlo?

- 🪶 **Lightweight**: Zero dependencies, minimal footprint
- ✨ **Simple**: Intuitive fluent API, easy to learn
- 🛡️ **Secure by Default**: Built-in SQL injection protection
- 🐍 **Pythonic**: Fluent API design that feels natural to Python developers
- 🧩 **Composable**: Build complex queries from reusable parts
- 🚀 **Extensible**: Support for custom dialects and functions
- 🔍 **Type-Safe**: Designed with type hints for better IDE support
- ✅ **Well-Tested**: 99% code coverage with comprehensive security tests

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
# SQL: SELECT `id`, `name` FROM `users` WHERE `active` = %s
# Params: (True,)

# INSERT query
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"}
])
sql, params = query.build()
```

## Documentation

Full documentation is available at **[https://nan-guo.github.io/sqlo/](https://nan-guo.github.io/sqlo/)**.

You can also browse the markdown files on GitHub:

- [Getting Started](https://github.com/nan-guo/sqlo/blob/main/docs/getting-started.md)
- [Security Guide](https://github.com/nan-guo/sqlo/blob/main/docs/security.md) ⭐
- [SELECT Queries](https://github.com/nan-guo/sqlo/blob/main/docs/select.md)
- [INSERT Queries](https://github.com/nan-guo/sqlo/blob/main/docs/insert.md)
- [UPDATE Queries](https://github.com/nan-guo/sqlo/blob/main/docs/update.md)
- [DELETE Queries](https://github.com/nan-guo/sqlo/blob/main/docs/delete.md)
- [JOIN Operations](https://github.com/nan-guo/sqlo/blob/main/docs/joins.md)
- [Condition Objects](https://github.com/nan-guo/sqlo/blob/main/docs/conditions.md)
- [Expressions & Functions](https://github.com/nan-guo/sqlo/blob/main/docs/expressions.md)

## License

MIT License
