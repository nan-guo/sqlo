# DELETE Queries

Complete guide to DELETE query building with sqlo.

## Basic DELETE

### Simple Delete

```python
from sqlo import Q

# ❌ ERROR: DELETE requires WHERE clause or explicit confirmation
try:
    query = Q.delete_from("users")
    sql, params = query.build()
except ValueError as e:
    print(e)  # "DELETE without WHERE clause would affect all rows..."
```

> [!WARNING]
> **DELETE Safety**: sqlo requires either a WHERE clause or explicit `.allow_all_rows()` to prevent accidental mass deletions.

### Delete All Rows (with confirmation)

```python
# Delete ALL rows (requires explicit confirmation)
query = Q.delete_from("temp_logs").allow_all_rows()
sql, params = query.build()
# DELETE FROM `temp_logs`
```

### Delete with WHERE

```python
# Delete specific rows (recommended)
query = Q.delete_from("users").where("id", 123)
sql, params = query.build()
# DELETE FROM `users` WHERE `id` = %s
# Params: (123,)
```

## WHERE Clause

### Basic Conditions

```python
# Single condition
query = Q.delete_from("users").where("active", False)

# Multiple AND conditions
query = (
    Q.delete_from("logs")
    .where("level", "debug")
    .where("created_at <", "2023-01-01")
)
# DELETE FROM `logs` WHERE `level` = %s AND `created_at` < %s
```

### OR Conditions

```python
query = (
    Q.delete_from("users")
    .where("status", "banned")
    .or_where("login_attempts >", 10)
)
# DELETE FROM `users` WHERE `status` = %s OR `login_attempts` > %s
```

### IN Clause

```python
query = Q.delete_from("users").where_in("id", [1, 2, 3, 4, 5])
# DELETE FROM `users` WHERE `id` IN (%s, %s, %s, %s, %s)
```

### NULL Checks

```python
# Delete rows with NULL values
query = Q.delete_from("tokens").where_null("expires_at")
# DELETE FROM `tokens` WHERE `expires_at` IS NULL
```

## ORDER BY and LIMIT

Control which rows are deleted (useful for pruning):

```python
# Delete oldest 100 logs
query = (
    Q.delete_from("logs")
    .order_by("created_at")  # Ascending order (oldest first)
    .limit(100)
)
# DELETE FROM `logs` ORDER BY `created_at` ASC LIMIT 100

# Delete newest records (e.g., undo recent imports)
query = (
    Q.delete_from("imports")
    .order_by("-created_at")  # Descending order
    .limit(10)
)
# DELETE FROM `imports` ORDER BY `created_at` DESC LIMIT 10
```

## Advanced Usage

### Multi-Table DELETE (MySQL)

Delete from multiple tables using JOINs:

```python
# Delete users who have no orders
query = (
    Q.delete_from("users")
    .left_join("orders", "orders.user_id = users.id")
    .where_null("orders.id")
)
# DELETE `users` FROM `users` LEFT JOIN `orders` ON orders.user_id = users.id WHERE `orders`.`id` IS NULL
```

### DELETE with Subquery

```python
# Delete users based on subquery
subquery = Q.select("user_id").from_("blacklisted_emails")

query = (
    Q.delete_from("users")
    .where_in("id", subquery)
)
# DELETE FROM `users` WHERE `id` IN (SELECT `user_id` FROM `blacklisted_emails`)
```

## Safety Best Practices

### 1. Always Use WHERE

Never run `Q.delete_from("table")` without a WHERE clause unless you intentionally want to truncate the table.

### 2. Use Soft Deletes Instead

Consider using "Soft Deletes" (updating a `deleted_at` timestamp) instead of actual DELETE queries for important data.

```python
# Instead of DELETE:
# query = Q.delete_from("users").where("id", 123)

# Use UPDATE:
query = (
    Q.update("users")
    .set({"deleted_at": "NOW()"})
    .where("id", 123)
)
```

### 3. Limit Deletions

When running cleanup jobs, use `limit()` to avoid locking the table for too long.

```python
# Delete in batches of 1000
query = (
    Q.delete_from("logs")
    .where("created_at <", "2022-01-01")
    .limit(1000)
)
```

### 4. Verify Before Execution

```python
def safe_delete(table_name, conditions):
    if not conditions:
        raise ValueError("Cannot delete without conditions!")
    
    query = Q.delete_from(table_name)
    for col, val in conditions.items():
        query = query.where(col, val)
        
    return query
```

## Common Patterns

### Pruning Old Data

```python
from datetime import datetime, timedelta

# Delete logs older than 30 days
cutoff_date = datetime.now() - timedelta(days=30)

query = (
    Q.delete_from("app_logs")
    .where("created_at <", cutoff_date)
    .limit(5000)  # Limit batch size
)
```

### Duplicate Removal

```python
# Keep only the latest entry for each user_id (MySQL specific trick)
# This is complex and often better done with a temporary table or multiple queries
```

## See Also

- [UPDATE Queries](update.md) - Soft delete implementation
- [SELECT Queries](select.md) - Selecting data to verify before delete
- [Condition Objects](conditions.md) - Complex conditions
