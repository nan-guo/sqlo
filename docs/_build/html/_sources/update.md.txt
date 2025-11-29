# UPDATE Queries

Complete guide to UPDATE query building with sqlo.

## Basic UPDATE

### Simple Update

```python
from sqlo import Q

# ❌ ERROR: UPDATE requires WHERE clause or explicit confirmation
try:
    query = Q.update("users").set({"active": False})
    sql, params = query.build()
except ValueError as e:
    print(e)  # "UPDATE without WHERE clause would affect all rows..."
```

> [!WARNING]
> **UPDATE Safety**: sqlo requires either a WHERE clause or explicit `.allow_all_rows()` to prevent accidental mass updates.

### Update with allow_all_rows()

```python
# Update ALL rows (requires explicit confirmation)
query = Q.update("users").set({"active": False}).allow_all_rows()
sql, params = query.build()
# UPDATE `users` SET `active` = %s
# Params: (False,)
```

### Update with WHERE

```python
# Update specific rows (recommended)
query = (
    Q.update("users")
    .set({"active": False})
    .where("id", 123)
)

sql, params = query.build()
# UPDATE `users` SET `active` = %s WHERE `id` = %s
# Params: (False, 123)
```

## SET Clause

### Update Multiple Columns

```python
query = (
    Q.update("users")
    .set({
        "name": "Alice Smith",
        "email": "alice.smith@example.com",
        "updated_at": "NOW()"
    })
    .where("id", 123)
)

# UPDATE `users` SET `name` = %s, `email` = %s, `updated_at` = NOW() WHERE `id` = %s
```

### Increment/Decrement Values

```python
# Increment a counter
query = (
    Q.update("users")
    .set({"login_count": "login_count + 1"})
    .where("id", 123)
)

# UPDATE `users` SET `login_count` = login_count + 1 WHERE `id` = %s

# Decrement a value
query = (
    Q.update("products")
    .set({"stock": "stock - 1"})
    .where("id", 456)
)

# UPDATE `products` SET `stock` = stock - 1 WHERE `id` = %s
```

### Using Expressions

```python
from sqlo import Raw

# Use raw SQL expressions
query = (
    Q.update("users")
    .set({
        "full_name": Raw("CONCAT(first_name, ' ', last_name)"),
        "updated_at": Raw("NOW()")
    })
    .where("id", 123)
)

# UPDATE `users` SET `full_name` = CONCAT(first_name, ' ', last_name), `updated_at` = NOW() WHERE `id` = %s
```

## WHERE Clause

### Basic Conditions

```python
# Single condition
query = Q.update("users").set({"active": False}).where("email", "test@example.com")

# Multiple AND conditions
query = (
    Q.update("users")
    .set({"active": False})
    .where("last_login <", "2020-01-01")
    .where("email_verified", False)
)
# WHERE `last_login` < %s AND `email_verified` = %s
```

### OR Conditions

```python
query = (
    Q.update("users")
    .set({"status": "inactive"})
    .where("last_login <", "2020-01-01")
    .or_where("login_count", 0)
)
# WHERE `last_login` < %s OR `login_count` = %s
```

### IN Clause

```python
query = (
    Q.update("users")
    .set({"group": "premium"})
    .where_in("id", [1, 2, 3, 4, 5])
)
# WHERE `id` IN (%s, %s, %s, %s, %s)
```

### NULL Checks

```python
# Update rows where column is NULL
query = (
    Q.update("users")
    .set({"email_verified_at": "NOW()"})
    .where_null("email_verified_at")
    .where("email_sent", True)
)
# WHERE `email_verified_at` IS NULL AND `email_sent` = %s
```

### Complex Conditions

```python
from sqlo import Condition

# Complex condition with AND/OR
condition = Condition.and_(
    Condition("active", "=", True),
    Condition.or_(
        Condition("role", "=", "admin"),
        Condition("role", "=", "moderator")
    )
)

query = (
    Q.update("users")
    .set({"permissions": "elevated"})
    .where(condition)
)
# WHERE (`active` = %s AND (`role` = %s OR `role` = %s))
```

See [Condition Objects](conditions.md) for more details.

## ORDER BY

Control the order in which rows are updated (useful with LIMIT):

```python
# Update oldest records first
query = (
    Q.update("users")
    .set({"processed": True})
    .where("processed", False)
    .order_by("created_at")  # Ascending order
    .limit(100)
)
# UPDATE `users` SET `processed` = %s WHERE `processed` = %s ORDER BY `created_at` ASC LIMIT 100

# Update newest records first
query = (
    Q.update("users")
    .set({"priority": "high"})
    .where("status", "pending")
    .order_by("-created_at")  # Descending order (prefix with -)
    .limit(50)
)
# ORDER BY `created_at` DESC LIMIT 50
```

## LIMIT

Limit the number of rows to update:

```python
# Update only first 100 matching rows
query = (
    Q.update("users")
    .set({"active": False})
    .where("last_login <", "2020-01-01")
    .limit(100)
)
# UPDATE `users` SET `active` = %s WHERE `last_login` < %s LIMIT 100
```

### Batch Updates with LIMIT

```python
def batch_update(condition_value, batch_size=1000):
    """Update in batches to avoid locking too many rows"""
    query = (
        Q.update("users")
        .set({"migrated": True})
        .where("migrated", False)
        .where("created_at <", condition_value)
        .limit(batch_size)
    )
    return query

# Execute in a loop until no more rows are affected
# while True:
#     query = batch_update("2023-01-01", batch_size=1000)
#     sql, params = query.build()
#     cursor.execute(sql, params)
#     if cursor.rowcount == 0:
#         break
```

## Dynamic UPDATE Building

### Partial Updates

```python
def partial_update(table: str, id_value: int, updates: dict):
    """Update only non-None values"""
    # Filter out None values
    clean_updates = {k: v for k, v in updates.items() if v is not None}
    
    if not clean_updates:
        raise ValueError("No values to update")
    
    query = (
        Q.update(table)
        .set(clean_updates)
        .where("id", id_value)
    )
    
    return query

# Usage
query = partial_update("users", 123, {
    "name": "Alice",
    "email": None,  # Will be excluded
    "age": 25
})
# UPDATE `users` SET `name` = %s, `age` = %s WHERE `id` = %s
```

## Advanced Examples

### Update with Subquery

```python
# Update based on aggregated data from another table
subquery = (
    Q.select("AVG(rating)")
    .from_("reviews")
    .where("reviews.product_id = products.id")
)

query = (
    Q.update("products")
    .set({"avg_rating": subquery})
    .where("id", 123)
)
# UPDATE `products` SET `avg_rating` = (SELECT AVG(rating) FROM `reviews` WHERE reviews.product_id = products.id) WHERE `id` = %s
```

### Conditional Value Updates

```python
# Update with CASE-like logic using expressions
query = (
    Q.update("users")
    .set({
        "status": Raw("CASE WHEN login_count > 100 THEN 'active' WHEN login_count > 10 THEN 'regular' ELSE 'new' END")
    })
    .where("status", "pending")
)
```

### Update Multiple Tables (MySQL)

> [!NOTE]
> Multi-table UPDATE is MySQL-specific and not supported by all databases.

```python
# Update with JOIN
query = (
    Q.update("users u")
    .join("user_profiles p", "p.user_id = u.id")
    .set({
        "u.last_profile_update": "NOW()",
        "p.updated_at": "NOW()"
    })
    .where("p.bio", None)
)
# UPDATE `users` `u` INNER JOIN `user_profiles` `p` ON p.user_id = u.id
# SET `u`.`last_profile_update` = NOW(), `p`.`updated_at` = NOW()
# WHERE `p`.`bio` IS NULL
```

### Bulk Status Update

```python
def update_user_status(user_ids: list[int], new_status: str):
    """Update status for multiple users"""
    query = (
        Q.update("users")
        .set({
            "status": new_status,
            "updated_at": "NOW()"
        })
        .where_in("id", user_ids)
    )
    return query

# Usage
query = update_user_status([1, 2, 3, 4, 5], "verified")
# UPDATE `users` SET `status` = %s, `updated_at` = NOW() WHERE `id` IN (%s, %s, %s, %s, %s)
```

### Increment with Bounds

```python
# Increment but don't exceed maximum
query = (
    Q.update("users")
    .set({"points": Raw("LEAST(points + 10, 1000)")})  # Max 1000 points
    .where("id", 123)
)
# UPDATE `users` SET `points` = LEAST(points + 10, 1000) WHERE `id` = %s

# Decrement but don't go below minimum
query = (
    Q.update("products")
    .set({"stock": Raw("GREATEST(stock - 1, 0)")})  # Min 0 stock
    .where("id", 456)
)
# UPDATE `products` SET `stock` = GREATEST(stock - 1, 0) WHERE `id` = %s
```

## Safety Best Practices

### Always Use WHERE

```python
# ❌ DANGEROUS: Updates ALL rows
query = Q.update("users").set({"active": False})

# ✅ SAFE: Updates specific rows
query = Q.update("users").set({"active": False}).where("id", 123)
```

### Validate Before Update

```python
def safe_update(table: str, updates: dict, conditions: dict):
    """Ensure WHERE clause is always present"""
    if not conditions:
        raise ValueError("UPDATE without WHERE clause is not allowed")
    
    query = Q.update(table).set(updates)
    
    for column, value in conditions.items():
        query = query.where(column, value)
    
    return query

# Usage
query = safe_update(
    "users",
    updates={"active": False},
    conditions={"id": 123}
)
```

### Use Transactions

```python
# When updating related data, use transactions
# (Note: Transaction handling is done at the database connection level)

# Example:
# with connection.transaction():
#     # Update user
#     query1 = Q.update("users").set({"status": "premium"}).where("id", 123)
#     cursor.execute(*query1.build())
#     
#     # Update user profile
#     query2 = Q.update("user_profiles").set({"tier": "premium"}).where("user_id", 123)
#     cursor.execute(*query2.build())
```

### Verify Row Count

```python
# After executing UPDATE, check affected rows
# query = Q.update("users").set({"active": False}).where("id", 123)
# sql, params = query.build()
# cursor.execute(sql, params)
# 
# if cursor.rowcount == 0:
#     # No rows were updated - ID might not exist
#     raise ValueError(f"User with id {123} not found")
# elif cursor.rowcount > 1:
#     # Multiple rows updated - might indicate a problem
#     raise ValueError(f"Expected to update 1 row, but updated {cursor.rowcount}")
```

## Performance Tips

### Use Indexes

```python
# Ensure WHERE clause columns are indexed
query = (
    Q.update("users")
    .set({"last_seen": "NOW()"})
    .where("email", "alice@example.com")  # Make sure 'email' is indexed
)
```

### Batch Updates

```python
# Instead of updating one row at a time in a loop
# ❌ Bad: N queries
for user_id in user_ids:
    query = Q.update("users").set({"active": True}).where("id", user_id)
    # Execute...

# ✅ Good: 1 query
query = (
    Q.update("users")
    .set({"active": True})
    .where_in("id", user_ids)
)
# Execute once
```

### Use LIMIT for Large Updates

```python
# Update in smaller batches to reduce lock time
def update_in_batches(batch_size=1000):
    affected = batch_size
    total = 0
    
    while affected == batch_size:
        query = (
            Q.update("users")
            .set({"migrated": True})
            .where("migrated", False)
            .limit(batch_size)
        )
        sql, params = query.build()
        # cursor.execute(sql, params)
        # affected = cursor.rowcount
        total += affected
    
    return total
```

## Common Patterns

### Update Timestamp

```python
# Always update 'updated_at' timestamp
query = (
    Q.update("users")
    .set({
        "name": "Alice",
        "updated_at": "NOW()"
    })
    .where("id", 123)
)
```

### Toggle Boolean

```python
# Toggle a boolean value
query = (
    Q.update("users")
    .set({"active": Raw("NOT active")})
    .where("id", 123)
)
# UPDATE `users` SET `active` = NOT active WHERE `id` = %s
```

### Update JSON Field

```python
import json

# Update JSON column
query = (
    Q.update("settings")
    .set({
        "preferences": json.dumps({"theme": "dark", "language": "en"})
    })
    .where("user_id", 123)
)
```

### Soft Delete

```python
# Implement soft delete pattern
def soft_delete(table: str, id_value: int):
    return (
        Q.update(table)
        .set({
            "deleted_at": "NOW()",
            "active": False
        })
        .where("id", id_value)
        .where_null("deleted_at")  # Only delete if not already deleted
    )

# Usage
query = soft_delete("users", 123)
```

## See Also

- [SELECT Queries](select.md) - Querying data
- [DELETE Queries](delete.md) - Deleting data
- [Condition Objects](conditions.md) - Complex conditions
- [Expressions & Functions](expressions.md) - SQL expressions
