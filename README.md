# sqlo

[![CI](https://github.com/nan-guo/sqlo/actions/workflows/ci.yml/badge.svg)](https://github.com/nan-guo/sqlo/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlo)](https://pypi.org/project/sqlo/)
[![Documentation](https://img.shields.io/badge/docs-github%20pages-blue)](https://sqlo.readthedocs.io/en/stable/)
[![License](https://img.shields.io/github/license/nan-guo/sqlo)](LICENSE)

A **lightweight** and **powerful** SQL query builder for Python. Build SQL queries with a clean, intuitive API while staying safe from SQL injection. Support for JSON fields, CTEs, batch updates, and more!

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

## Documentation
https://sqlo.readthedocs.io/en/stable/

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

## Debug Mode
### Global Debug Mode
Enable debug mode to automatically print all queries:
```python
from sqlo import Q
# Enable debug mode globally
Q.set_debug(True)
query = Q.select("*").from_("users").where("id", 1)
sql, params = query.build()
# Automatically prints:
# [sqlo DEBUG] SELECT * FROM `users` WHERE `id` = %s
# [sqlo DEBUG] Params: (1,)
# Disable debug mode
Q.set_debug(False)
```

### Query Debug Mode

You can also enable debug mode for a specific query:
```python
from sqlo import Q
query = Q.select("*").from_("users").where("id", 1).debug()
sql, params = query.build(
# Prints debug output for this query only
# [sqlo DEBUG] SELECT * FROM `users` WHERE `id` = %s
# [sqlo DEBUG] Params: (1,)
```

## JSON Field Support
Query JSON columns with ease:
```python
from sqlo import Q, JSON

# Extract JSON fields in SELECT
query = Q.select("id", JSON("data").extract("name").as_("name")).from_("users")
# SQL: SELECT `id`, `data`->>'$.name' AS `name` FROM `users`

# Filter by JSON fields
query = Q.select("*").from_("users").where(JSON("data").extract("age"), 18, ">")
# SQL: SELECT * FROM `users` WHERE `data`->>'$.age' > %s
```

## Batch Updates
Efficiently update multiple rows with different values:
```python
values = [
    {"id": 1, "name": "Alice", "status": "active"},
    {"id": 2, "name": "Bob", "status": "inactive"},
]
query = Q.update("users").batch_update(values, key="id")
# Generates optimized CASE WHEN SQL
```

## Common Table Expressions (CTE)
Build complex queries with CTEs:
```python
from sqlo import Q, func

# Define a CTE
cte = Q.select("user_id", func.count("*").as_("order_count")) \
    .from_("orders") \
    .group_by("user_id") \
    .as_("user_orders")

# Use it in main query
query = Q.select("u.name", "uo.order_count") \
    .with_(cte) \
    .from_("users", alias="u") \
    .join("user_orders uo", "u.id = uo.user_id")
```

## Window Functions
Perform advanced analytics with window functions:
```python
from sqlo import Q, Window, func

# Ranking within partitions
query = Q.select(
    "name",
    "department",
    "salary",
    func.row_number().over(
        Window.partition_by("department").and_order_by("-salary")
    ).as_("rank")
).from_("employees")
# SQL: SELECT `name`, `department`, `salary`,
#   ROW_NUMBER() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
# FROM `employees`

# Running totals
query = Q.select(
    "date",
    "amount",
    func.sum("amount").over(
        Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
    ).as_("running_total")
).from_("transactions")

# LAG and LEAD for time series
query = Q.select(
    "date",
    "value",
    func.lag("value", 1).over(Window.order_by("date")).as_("prev_value"),
    func.lead("value", 1).over(Window.order_by("date")).as_("next_value")
).from_("metrics")
```

## Documentation

Full documentation is available at **[https://sqlo.readthedocs.io/en/stable/](https://sqlo.readthedocs.io/en/stable/)**.

You can also browse the markdown files on GitHub:

- [Getting Started](https://github.com/nan-guo/sqlo/blob/main/docs/getting-started.md)
- [Security Guide](https://github.com/nan-guo/sqlo/blob/main/docs/security.md)
- [SELECT Queries](https://github.com/nan-guo/sqlo/blob/main/docs/select.md)
- [INSERT Queries](https://github.com/nan-guo/sqlo/blob/main/docs/insert.md)
- [UPDATE Queries](https://github.com/nan-guo/sqlo/blob/main/docs/update.md)
- [DELETE Queries](https://github.com/nan-guo/sqlo/blob/main/docs/delete.md)
- [JOIN Operations](https://github.com/nan-guo/sqlo/blob/main/docs/joins.md)
- [Condition Objects](https://github.com/nan-guo/sqlo/blob/main/docs/conditions.md)
- [Expressions & Functions](https://github.com/nan-guo/sqlo/blob/main/docs/expressions.md)

## License

MIT License
