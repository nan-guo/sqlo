# Security Guide

This guide explains security best practices when using dm-core-sql-toolkit to prevent SQL injection attacks.

## Overview

dm-core-sql-toolkit uses **parameterized queries** by default, which prevents SQL injection for **values**. However, **table names**, **field names**, and other SQL identifiers are directly inserted into SQL strings and must be validated.

## SQL Injection Prevention

### ✅ Safe: Parameterized Queries (Default)

The toolkit automatically uses parameterized queries for all values:

```python
from sqlo.query_builder import select_from

# ✅ SAFE: User input is parameterized
user_email = "admin@example.com'; DROP TABLE users; --"
query = select_from("users").where("email = %s", user_email)
# SQL: SELECT * FROM users WHERE email = %s
# Params: ("admin@example.com'; DROP TABLE users; --",)
```

The malicious SQL is treated as a **value**, not as SQL code, so it cannot execute.

### ❌ Unsafe: Using `is_raw=True` with User Input

**NEVER** use `is_raw=True` with user input:

```python
# ❌ DANGEROUS: SQL injection vulnerability
user_input = "admin@example.com'; DROP TABLE users; --"
query = select_from("users").where(
    f"email = '{user_input}'", 
    is_raw=True  # ⚠️ NEVER DO THIS WITH USER INPUT
)
# SQL: SELECT * FROM users WHERE email = 'admin@example.com'; DROP TABLE users; --'
```

**When to use `is_raw=True`**:
- Only with **hardcoded, trusted SQL strings**
- Never with user-provided input
- Example: `where("created_at > NOW() - INTERVAL 1 DAY", is_raw=True)`

### ❌ Unsafe: User Input as Table/Field Names

**NEVER** use user input directly as table or field names:

```python
# ❌ DANGEROUS: SQL injection vulnerability
user_table = "users; DROP TABLE users; --"
query = select_from(user_table)  # ⚠️ NEVER DO THIS

user_field = "id; DROP TABLE users; --"
query = select_from("users").select_fields(user_field)  # ⚠️ NEVER DO THIS
```

## Best Practices

### 1. Validate Identifiers

Use the `security` module to validate table and field names:

```python
from sqlo import security
from sqlo.query_builder import select_from

# Validate before use
user_table = request.args.get("table")
if not security.validate_identifier(user_table):
    raise ValueError("Invalid table name")

query = select_from(user_table)  # Now safe
```

### 2. Use Whitelists (Recommended)

The safest approach is to use a whitelist of allowed identifiers:

```python
from sqlo import security
from sqlo.query_builder import select_from

# Define allowed tables
ALLOWED_TABLES = {"users", "orders", "products"}

user_table = request.args.get("table")
if not security.validate_identifier_whitelist(user_table, ALLOWED_TABLES):
    raise ValueError("Table not allowed")

query = select_from(user_table)  # Safe
```

### 3. Escape Identifiers (MySQL)

For MySQL, you can escape identifiers with backticks:

```python
from sqlo import security
from sqlo.query_builder import select_from

# Validate first
table_name = "users"
if security.validate_identifier(table_name):
    # Escape for safety (though validation should be enough)
    escaped_table = security.escape_identifier(table_name)
    # Note: The query builder doesn't use this automatically
    # This is just for reference
```

**Note**: The query builder doesn't automatically escape identifiers. You should validate them instead.

## Common Patterns

### Safe Dynamic Table Selection

```python
from sqlo import security
from sqlo.query_builder import select_from

ALLOWED_TABLES = {"users", "orders", "products"}

def get_data(table_name: str, user_id: int):
    # Validate table name
    if not security.validate_identifier_whitelist(table_name, ALLOWED_TABLES):
        raise ValueError(f"Invalid table: {table_name}")
    
    # Safe: table name is validated, user_id is parameterized
    query = select_from(table_name).where("id = %s", user_id)
    return query
```

### Safe Dynamic Field Selection

```python
from sqlo import security
from sqlo.query_builder import select_from

ALLOWED_FIELDS = {"id", "name", "email", "created_at"}

def get_user_fields(fields: list[str], user_id: int):
    # Validate all fields
    if not all(security.validate_identifier_whitelist(f, ALLOWED_FIELDS) for f in fields):
        raise ValueError("Invalid field name")
    
    # Safe: fields are validated, user_id is parameterized
    query = select_from("users").select_fields(*fields).where("id = %s", user_id)
    return query
```

### Safe Dynamic Sorting

```python
from sqlo import security
from sqlo.query_builder import select_from

ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "name"}

def get_users_sorted(sort_field: str, sort_order: str = "ASC"):
    # Validate sort field
    if not security.validate_identifier_whitelist(sort_field, ALLOWED_SORT_FIELDS):
        raise ValueError(f"Invalid sort field: {sort_field}")
    
    # Validate sort order
    if sort_order.upper() not in {"ASC", "DESC"}:
        raise ValueError(f"Invalid sort order: {sort_order}")
    
    # Safe: sort_field is validated, sort_order is validated
    query = select_from("users").order_by((sort_field, sort_order))
    return query
```

## Security Checklist

When using dm-core-sql-toolkit, always:

- ✅ Use parameterized queries for all **values** (default behavior)
- ✅ Validate **table names** before use (use whitelist if possible)
- ✅ Validate **field names** before use (use whitelist if possible)
- ✅ Never use `is_raw=True` with user input
- ✅ Never use user input directly as table/field names
- ✅ Use the `security` module for validation
- ✅ Prefer whitelists over pattern matching when possible

## Additional Resources

- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Python SQL Injection Prevention](https://pynative.com/python-sql-injection/)

