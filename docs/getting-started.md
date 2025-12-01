# Getting Started

Quick start guide for sqlo.

## Installation

```bash
pip install sqlo
```

Or using PDM:

```bash
pdm add sqlo
```

## Quick Examples

### Basic Queries

```python
from sqlo import Q

# SELECT query
query = Q.select("id", "name").from_("users").where("active", True)
sql, params = query.build()
# SQL: SELECT `id`, `name` FROM `users` WHERE `active` = %s
# Params: (True,)
```

### INSERT Data

```python
# Single row insert
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"}
])
sql, params = query.build()

# Batch insert
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"}
])
sql, params = query.build()
```

### UPDATE Data

```python
query = (
    Q.update("users")
    .set({"active": False})
    .where("last_login <", "2020-01-01")
    .limit(100)
)
sql, params = query.build()
```

### DELETE Data

```python
query = Q.delete_from("users").where("id", 123)
sql, params = query.build()
```

## Core Concepts

### 1. Q Factory Class

`Q` is the entry point for all queries:

- `Q.select(...)` - Create SELECT query
- `Q.insert_into(...)` - Create INSERT query
- `Q.update(...)` - Create UPDATE query
- `Q.delete_from(...)` - Create DELETE query

### 2. Fluent API

All queries support method chaining:

```python
query = (
    Q.select("*")
    .from_("users")
    .where("age >", 18)
    .order_by("-created_at")
    .limit(10)
)
```

### 3. Parameterized Queries

Automatically generates parameterized queries to prevent SQL injection:

```python
query = Q.select("*").from_("users").where("email", user_input)
sql, params = query.build()
# user_input is never directly concatenated into SQL
```

### 4. SQL Dialects

`sqlo` uses **MySQL** as the default dialect. This affects:
- Identifier quoting: `` `table_name` ``
- Parameter placeholders: `%s`

```python
from sqlo import Q

# By default, uses MySQL dialect
query = Q.select("*").from_("users").where("id", 1)
sql, params = query.build()
# SQL: SELECT * FROM `users` WHERE `id` = %s
# Params: (1,)
```

#### Changing the Dialect

You can change the default dialect for your entire application:

```python
from sqlo import Q
from sqlo.dialects.mysql import MySQLDialect

# Set the dialect globally (optional, MySQL is already default)
Q.set_dialect(MySQLDialect())

# All queries will use this dialect
query = Q.select("*").from_("users")
```

## Debugging Queries

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

## Next Steps

- [SELECT Queries](select.md)
- [JOIN Operations](joins.md)
- [Condition Objects](conditions.md)
- [Complete API Reference](api-reference.md)
