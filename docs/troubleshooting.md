# Troubleshooting

Common issues and solutions when using sqlo.

## Installation Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'sqlo'`

**Solution**:
```bash
# Install sqlo
pip install sqlo

# Or with uv
uv add sqlo

# Verify installation
python -c "import sqlo; print(sqlo.__version__)"
```

### Version Conflicts

**Problem**: Incompatible Python version

**Solution**:
```bash
# sqlo requires Python 3.9+
python --version

# If using older version, upgrade Python
# Or use pyenv/uv to manage Python versions
```

## Query Building Errors

### Missing WHERE Clause

**Problem**: `ValueError: UPDATE without WHERE clause would affect all rows`

**Solution**:
```python
# ❌ Error: No WHERE clause
query = Q.update("users").set({"active": False})

# ✅ Fix 1: Add WHERE clause
query = Q.update("users").set({"active": False}).where("id", 123)

# ✅ Fix 2: Explicitly allow all rows
query = Q.update("users").set({"active": False}).allow_all_rows()
```

**Same applies to DELETE**:
```python
# ❌ Error
query = Q.delete_from("users")

# ✅ Fix
query = Q.delete_from("users").where("inactive", True)
# Or
query = Q.delete_from("users").allow_all_rows()
```

### CTE Without Name

**Problem**: `ValueError: CTE must have a name. Use .as_('name') method.`

**Solution**:
```python
# ❌ Error: CTE without name
cte = Q.select("*").from_("users").where("active", True)
query = Q.select("*").with_(cte).from_("active_users")

# ✅ Fix: Name the CTE
cte = Q.select("*").from_("users").where("active", True).as_("active_users")
query = Q.select("*").with_(cte).from_("active_users")
```

### Invalid Identifiers

**Problem**: `ValueError: Invalid table/column name`

**Solution**:
```python
# ❌ Error: Invalid characters
query = Q.select("*").from_("users; DROP TABLE users")

# ✅ Fix: Use only valid identifiers (alphanumeric, underscore, dot)
query = Q.select("*").from_("users")

# For complex expressions, use Raw
from sqlo import Raw
query = Q.select(Raw("COUNT(*)")).from_("users")
```

### Empty IN Clause

**Problem**: Unexpected behavior with empty lists in `WHERE IN`

**Solution**:
```python
# sqlo automatically handles empty lists
ids = []

# Generates: WHERE FALSE (never matches)
query = Q.select("*").from_("users").where_in("id", ids)

# NOT IN with empty list generates: WHERE TRUE (matches all)
query = Q.select("*").from_("users").where_not_in("id", ids)

# Better: Check before building query
if ids:
    query = Q.select("*").from_("users").where_in("id", ids)
else:
    # Handle empty case explicitly
    query = Q.select("*").from_("users").where(Raw("FALSE"))
```

## SQL

 Generation Issues

### Incorrect Column Quoting

**Problem**: Columns not properly quoted

**Expected**: Columns should be automatically quoted with backticks

**Solution**:
```python
# Columns are auto-quoted
query = Q.select("order", "group").from_("select")
# SELECT `order`, `group` FROM `select`

# For raw SQL, quote manually
from sqlo import Raw
query = Q.select(Raw("`order` + 1")).from_("items")
```

### Parameter Binding Issues

**Problem**: Parameters not properly bound

**Solution**:
```python
# ✅ Correct: Parameterized
query = Q.select("*").from_("users").where("name", user_input)
sql, params = query.build()
# SQL: WHERE `name` = %s
# Params: (user_input,)

# ❌ Incorrect: String interpolation (SQL injection risk!)
query = Q.select("*").from_("users").where(Raw(f"name = '{user_input}'"))
```

## Runtime Errors

### MySQL Errors

**Problem**: `MySQL Error 1064: Syntax error`

**Debug**: Use debug mode to see generated SQL
```python
query = Q.select("*").from_("users").where("id", 123).debug()
sql, params = query.build()
# Prints SQL and parameters
```

**Common causes**:
1. Reserved keywords not quoted
2. Incorrect dialect
3. Complex Raw expressions

**Solution**:
```python
# 1. Reserved keywords (auto-handled)
query = Q.select("order").from_("users")  # OK

# 2. Check dialect
Q.set_dialect("mysql")  # Default

# 3. Verify Raw expressions
from sqlo import Raw
# Make sure Raw SQL is valid
query = Q.select(Raw("COUNT(*)")).from_("users")
```

### Type Errors

**Problem**: `TypeError: 'NoneType' object is not iterable`

**Common cause**: Missing return value or None passed where list expected

**Solution**:
```python
# ❌ Error
values = None
query = Q.insert_into("users").values(values)

# ✅ Fix
values = [{"name": "Alice", "email": "alice@example.com"}]
query = Q.insert_into("users").values(values)

# Or check first
if values:
    query = Q.insert_into("users").values(values)
```

## Performance Issues

### Slow Queries

**Problem**: Query takes too long to execute

**Debug**:
```python
# Use EXPLAIN to analyze query plan
query = Q.select("*").from_("users").where("email", "test@example.com")
explain_query = query.explain()
sql, params = explain_query.build()

# Execute with database
# cursor.execute(sql, params)
# for row in cursor.fetchall():
#     print(row)
```

**Common fixes**:
1. Add indexes on WHERE columns
2. Use LIMIT to restrict results
3. Avoid SELECT *
4. Use joins instead of subqueries (or vice versa)

```python
# ❌ Slow: No limit
query = Q.select("*").from_("large_table").where("status", "active")

# ✅ Better: Add limit
query = Q.select("*").from_("large_table").where("status", "active").limit(100)

# ✅ Best: Select only needed columns
query = Q.select("id", "name").from_("large_table").where("status", "active").limit(100)
```

### Memory Issues

**Problem**: Out of memory when processing large result sets

**Solution**: Use pagination or streaming

```python
# Pagination
page = 1
per_page = 1000

while True:
    query = (
        Q.select("*")
        .from_("large_table")
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    
    # cursor.execute(*query.build())
    # rows = cursor.fetchall()
    # if not rows:
    #     break
    
    # Process batch
    # for row in rows:
    #     process(row)
    
    page += 1
```

## Testing Issues

### Assertion Failures

**Problem**: Generated SQL doesn't match expected

**Solution**: Use debug mode and compare
```python
query = Q.select("id", "name").from_("users").where("active", True)
sql, params = query.build()

# Debug: Print actual SQL
print(f"SQL: {sql}")
print(f"Params: {params}")

# Compare with expected
expected_sql = "SELECT `id`, `name` FROM `users` WHERE `active` = %s"
assert sql == expected_sql
assert params == (True,)
```

### Mock Database Issues

**Problem**: Tests fail with mock database

**Solution**: Test query building separately from execution
```python
# Test query building
def test_user_query():
    query = Q.select("*").from_("users").where("id", 123)
    sql, params = query.build()
    
    assert "SELECT" in sql
    assert "users" in sql
    assert params == (123,)

# Test execution separately with real/test database
def test_user_query_execution(db_connection):
    query = Q.select("*").from_("users").where("id", 123)
    cursor = db_connection.cursor()
    cursor.execute(*query.build())
    result = cursor.fetchone()
    assert result is not None
```

## IDE and Type Checking

### Type Hints Not Working

**Problem**: IDE doesn't show autocomplete

**Solution**:
```python
# Make sure you have type stubs
from sqlo import Q, Condition, Raw, func

# Use explicit types if needed
from sqlo.query.select import SelectQuery

query: SelectQuery = Q.select("*").from_("users")
```

### mypy Errors

**Problem**: mypy shows type errors

**Common causes**:
1. Mixed types in values
2. Incorrect method chaining

**Solution**:
```python
# Configure mypy (pyproject.toml)
# [tool.mypy]
# ignore_missing_imports = true

# Or use type: ignore for specific lines
query = Q.select("*").from_("users")  # type: ignore
```

## Common Mistakes

### Forgetting to Call build()

**Problem**: Passing query object instead of SQL

**Solution**:
```python
query = Q.select("*").from_("users").where("id", 123)

# ❌ Wrong: Passing query object
# cursor.execute(query)

# ✅ Correct: Extract SQL and params
sql, params = query.build()
cursor.execute(sql, params)
```

### Reusing Query Objects

**Problem**: Query objects are mutable

**Solution**:
```python
# Query objects can be reused and modified
base_query = Q.select("*").from_("users")

# These create new objects (method chaining returns new instances)
active_users = base_query.where("active", True)
inactive_users = base_query.where("active", False)

# Both are independent
```

### Mixing Dialects

**Problem**: Using features from different SQL dialects

**Solution**:
```python
# Set dialect globally
Q.set_dialect("mysql")

# Or per query (if supported in future versions)
# Currently sqlo only supports MySQL
```

## Getting Help

### Debug Mode

Always start by enabling debug mode:

```python
# Global debug
Q.set_debug(True)

query = Q.select("*").from_("users").where("id", 123)
sql, params = query.build()
# Automatically prints SQL and params

# Per-query debug
query = Q.select("*").from_("users").where("id", 123).debug()
```

### Check Version

```python
import sqlo
print(sqlo.__version__)

# Make sure you're using the latest version
# pip install --upgrade sqlo
```

### Report Issues

If you encounter a bug:

1. Check existing issues: https://github.com/nan-guo/sqlo/issues
2. Create minimal reproducible example
3. Include:
   - sqlo version
   - Python version
   - Generated SQL (from debug mode)
   - Expected vs actual behavior

```python
# Minimal example for bug report
from sqlo import Q

query = Q.select("*").from_("users").where("id", 123)
sql, params = query.build()

print(f"sqlo version: {sqlo.__version__}")
print(f"SQL: {sql}")
print(f"Params: {params}")
print(f"Expected: ...")
```

## See Also

- [Security Guide](security.md) - SQL injection prevention
- [Getting Started](getting-started.md) - Basic usage
- [API Reference](reference.md) - Complete API documentation
