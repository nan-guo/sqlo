# Security Guide

Complete guide to security features and best practices in sqlo.

## Security Features

sqlo implements multiple layers of security to prevent SQL injection attacks:

1. **Automatic parameter binding** for all values
2. **Mandatory identifier validation** for table and column names
3. **UPDATE/DELETE safety checks** to prevent accidental mass operations
4. **Type-safe Raw() expressions** with clear documentation
5. **Empty list handling** for safe WHERE IN operations

---

## Identifier Validation

### Automatic Validation

All table and column names are automatically validated to prevent SQL injection:

```python
from sqlo import Q

# ✅ Valid identifiers are allowed
Q.select("id", "name").from_("users").build()
Q.select("*").from_("mydb.users").build()  # schema.table format

# ❌ Invalid identifiers are rejected
Q.select("*").from_("users; DROP TABLE users;").build()
# Raises: ValueError: Invalid identifier 'users; DROP TABLE users;'
```

### What's Allowed

Valid identifiers must:
- Start with a letter or underscore
- Contain only letters, numbers, underscores, and dots
- Not contain spaces, special characters, or SQL keywords in vulnerable positions

**Examples:**
- ✅ `users`
- ✅ `user_accounts`
- ✅ `mydb.users` (schema.table)
- ✅ `users.id` (table.column)
- ❌ `users; DROP TABLE` (semicolon)
- ❌ `users--comment` (SQL comment)
- ❌ `users /*comment*/` (SQL comment)
- ❌ `users OR 1=1` (SQL injection attempt)

### Table Aliases

Table aliases with spaces are supported:

```python
# ✅ Allowed - validates "orders" part
Q.select("*").from_("users u").join("orders o", "u.id = o.user_id").build()
```

---

## Parameter Binding

### Automatic Protection

All **values** are automatically parameterized to prevent SQL injection:

```python
# ✅ SAFE - value is parameterized
malicious_input = "admin' OR '1'='1"
query = Q.select("*").from_("users").where("email", malicious_input)
sql, params = query.build()
# SQL: SELECT * FROM `users` WHERE `email` = %s
# Params: ("admin' OR '1'='1",)  # Treated as literal string
```

The malicious SQL is treated as a **string value**, not as executable SQL code.

---

## Raw SQL Expressions

### When to Use Raw()

Use `Raw()` for SQL expressions that cannot be represented as identifiers or values:

```python
from sqlo import Raw

# ✅ SQL functions
Q.select(Raw("COUNT(*)")).from_("users")
Q.select(Raw("CONCAT(first_name, ' ', last_name)")).from_("users")

# ✅ SQL expressions in WHERE
Q.select("*").from_("users").where(Raw("created_at > NOW() - INTERVAL 7 DAY"))

# ✅ Raw with parameters (still safe!)
Q.select("*").from_("users").where(Raw("age > %s", [18]))
```

### Safety Warning

> [!CAUTION]
> **Never use user input directly in Raw()** - this bypasses all security protections!

```python
# ❌ DANGEROUS - SQL injection vulnerability!
user_input = request.args.get("condition")
Q.select("*").from_("users").where(Raw(user_input))  # NEVER DO THIS!

# ✅ SAFE - validate/whitelist first, or use parameterized queries
allowed_fields = {"name", "email", "age"}
if field in allowed_fields:
    Q.select("*").from_("users").where(field, user_value)
```

### Type Checking

`Raw()` requires a string argument:

```python
from sqlo import Raw

# ✅ Valid
Raw("COUNT(*)")

# ❌ Invalid - raises TypeError
Raw(123)  # TypeError: Raw SQL must be a string
```

---

## UPDATE/DELETE Safety

### Mandatory WHERE Clause

To prevent accidental mass operations, UPDATE and DELETE require either:
1. A WHERE clause, or
2. Explicit `.allow_all_rows()` call

```python
# ❌ Raises ValueError - no WHERE clause
Q.update("users").set({"active": False}).build()
# ValueError: UPDATE without WHERE clause would affect all rows

# ✅ With WHERE clause
Q.update("users").set({"active": False}).where("id", 123).build()

# ✅ Explicit confirmation for mass operation
Q.update("users").set({"active": False}).allow_all_rows().build()
```

### The `.allow_all_rows()` Method

Use this method when you intentionally want to affect all rows:

```python
from sqlo import Q

# Mass update
Q.update("settings").set({"migrated": True}).allow_all_rows().build()

# Mass delete
Q.delete_from("temp_logs").allow_all_rows().build()

# With ORDER BY and LIMIT (still requires allow_all_rows without WHERE)
Q.delete_from("logs").order_by("-created_at").limit(1000).allow_all_rows().build()
```

---

## Empty List Handling

### WHERE IN with Empty Lists

Empty lists in `WHERE IN` clauses are automatically handled:

```python
# Empty IN list generates FALSE
sql, params = Q.select("*").from_("users").where_in("id", []).build()
# SQL: SELECT * FROM `users` WHERE FALSE
# Params: ()

# Empty NOT IN list generates TRUE
sql, params = Q.select("*").from_("users").where_not_in("id", []).build()
# SQL: SELECT * FROM `users` WHERE TRUE
# Params: ()
```

This ensures syntactically correct SQL even with dynamic lists.

---

## NULL Value Handling

### Correct NULL Checks

Use dedicated methods for NULL checks:

```python
from sqlo import Q, Condition

# ✅ Correct ways to check for NULL
Q.select("*").from_("users").where_null("email")  # Simplest
Q.select("*").from_("users").where(Condition.null("email"))  # Type-safe
Q.select("*").from_("users").where(Condition("email", operator="IS NULL"))

# ❌ WRONG - this checks for the STRING 'NULL', not SQL NULL
Q.select("*").from_("users").where("email", "NULL")
Q.select("*").from_("users").where(Condition("email", "NULL", "IS"))
```

### NULL in INSERT/UPDATE

NULL values in data dictionaries are properly handled:

```python
# ✅ NULL values work correctly
Q.insert_into("users").values({"name": "Alice", "email": None})
# email will be set to NULL

Q.update("users").set({"email": None}).where("id", 123)
# email will be set to NULL
```

---

## Best Practices

### 1. Always Validate Dynamic Identifiers

When allowing users to specify table or column names:

```python
from sqlo import Q

ALLOWED_TABLES = {"users", "orders", "products"}
ALLOWED_COLUMNS = {"id", "name", "email", "created_at"}

def dynamic_query(table: str, columns: list[str]):
    # Validate inputs
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not allowed")
    
    if not all(col in ALLOWED_COLUMNS for col in columns):
        raise ValueError("Invalid column name")
    
    # Safe to use
    return Q.select(*columns).from_(table)
```

### 2. Use Parameterized Queries for Values

Never concatenate user input into SQL strings:

```python
# ❌ DANGEROUS
user_email = request.form.get("email")
Q.select("*").from_("users").where(Raw(f"email = '{user_email}'"))

# ✅ SAFE
Q.select("*").from_("users").where("email", user_email)
```

### 3. Use Dedicated Methods

Prefer dedicated methods over generic ones:

```python
# Instead of Raw() or complex Conditions
Q.select("*").from_("users").where_null("deleted_at")  # Clear intent
Q.select("*").from_("users").where_in("status", ["active", "pending"])
Q.update("users").set({"active": False}).where("id", 123)
```

### 4. Verify Before Mass Operations

Always double-check before calling `.allow_all_rows()`:

```python
def archive_old_data(cutoff_date: str):
    """Archive data older than cutoff_date."""
    # Add confirmation in your application layer
    query = (
        Q.update("orders")
        .set({"archived": True})
        .where("created_at <", cutoff_date)
    )
    # Only use allow_all_rows() if truly necessary
    return query
```

### 5. Use Transactions for Related Operations

When performing multiple related operations:

```python
# Use database-level transactions
# with conn.transaction():
#     Q.update("users").set({"status": "deleted"}).where("id", user_id).execute()
#     Q.delete_from("sessions").where("user_id", user_id).execute()
```

---

## Security Checklist

When building queries with sqlo:

- ✅ Table and column names are validated automatically
- ✅ User values are parameterized automatically
- ✅ `Raw()` is only used with trusted, hardcoded SQL
- ✅ UPDATE and DELETE have WHERE clauses or explicit `.allow_all_rows()`
- ✅ NULL checks use `.where_null()` or `Condition.null()`
- ✅ Dynamic identifiers (table/column names) are whitelisted
- ✅ Empty lists in WHERE IN are handled correctly
- ✅ Type checking is enabled (`Raw()` rejects non-strings)

---

## Common Vulnerabilities and Prevention

### 1. Table Name Injection

**Vulnerability:**
```python
# ❌ Old approach - vulnerable
user_table = request.args.get("table")
Q.select("*").from_(user_table)  # Could be "users; DROP TABLE users;--"
```

**Protection:**
```python
# ✅ Now automatically blocked
Q.select("*").from_("users; DROP TABLE users;--")
# Raises: ValueError: Invalid identifier
```

### 2. Column Name Injection

**Protection:**
```python
# Automatically validates all column names
Q.select("id; DROP TABLE users;--").from_("users")
# Raises: ValueError: Invalid identifier
```

### 3. WHERE Clause Injection

**Protection:**
```python
# Values are automatically parameterized
malicious = "1' OR '1'='1"
Q.select("*").from_("users").where("name", malicious)
# Safe - malicious string is treated as a literal value
```

---

## Additional Resources

- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Condition Objects](conditions.md) - Type-safe query conditions
- [Expressions & Functions](expressions.md) - Using Raw() safely
