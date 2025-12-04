# Batch Operations

Complete guide to efficient batch operations with sqlo.

## Introduction

Batch operations allow you to process large datasets efficiently by grouping multiple operations together or processing data in chunks. This guide covers batch inserts, updates, and best practices for high-performance data operations.

## Batch INSERT

### Multiple Rows in Single Query

The most efficient way to insert multiple rows is with a single `INSERT` statement.

```python
from sqlo import Q

# Insert multiple users at once
users = [
    {"name": "Alice", "email": "alice@example.com", "active": True},
    {"name": "Bob", "email": "bob@example.com", "active": True},
    {"name": "Charlie", "email": "charlie@example.com", "active": False},
]

query = Q.insert_into("users").values(users)
sql, params = query.build()

# INSERT INTO `users` (`name`, `email`, `active`)
# VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s)
# Params: ('Alice', 'alice@example.com', True, 'Bob', ...)
```

### Chunked Batch INSERT

For very large datasets, split into manageable chunks to avoid hitting database limits.

```python
def batch_insert(table: str, data: list[dict], chunk_size: int = 1000):
    """Insert data in chunks to avoid overwhelming the database."""
    total_inserted = 0
    
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        query = Q.insert_into(table).values(chunk)
        sql, params = query.build()
        
        # cursor.execute(sql, params)
        # total_inserted += cursor.rowcount
        total_inserted += len(chunk)
    
    return total_inserted

# Usage
large_dataset = [{"name": f"User{i}", "email": f"user{i}@example.com"} for i in range(10000)]
batch_insert("users", large_dataset, chunk_size=500)
```

### INSERT IGNORE for Duplicates

```python
# Skip duplicate key errors
query = Q.insert_into("users").ignore().values([
    {"email": "alice@example.com", "name": "Alice"},
    {"email": "bob@example.com", "name": "Bob"}
])

# INSERT IGNORE INTO `users` ...
```

### ON DUPLICATE KEY UPDATE

```python
# Upsert: Insert or update if exists
query = (
    Q.insert_into("user_stats")
    .values([
        {"user_id": 1, "login_count": 1, "last_login": "2024-01-01"},
        {"user_id": 2, "login_count": 1, "last_login": "2024-01-01"}
    ])
    .on_duplicate_key_update({
        "login_count": "login_count + 1",
        "last_login": "VALUES(last_login)"
    })
)

# INSERT INTO `user_stats` ...
# ON DUPLICATE KEY UPDATE
#   `login_count` = login_count + 1,
#   `last_login` = VALUES(last_login)
```

## Batch UPDATE

### UPDATE with IN Clause

Update multiple rows with the same values.

```python
# Deactivate multiple users
user_ids = [1, 2, 3, 4, 5]

query = (
    Q.update("users")
    .set({"active": False, "updated_at": "NOW()"})
    .where_in("id", user_ids)
)

# UPDATE `users`
# SET `active` = %s, `updated_at` = NOW()
# WHERE `id` IN (%s, %s, %s, %s, %s)
```

### Batch UPDATE with Different Values

Use `batch_update()` for updating multiple rows with different values efficiently.

```python
# Update multiple rows with different values
updates = [
    {"id": 1, "name": "Alice Updated", "status": "active"},
    {"id": 2, "name": "Bob Updated", "status": "inactive"},
    {"id": 3, "name": "Charlie Updated", "status": "active"},
]

query = Q.update("users").batch_update(updates, key="id")

sql, params = query.build()
# UPDATE `users`
# SET `name` = CASE
#       WHEN `id` = %s THEN %s
#       WHEN `id` = %s THEN %s
#       WHEN `id` = %s THEN %s
#     END,
#     `status` = CASE
#       WHEN `id` = %s THEN %s
#       WHEN `id` = %s THEN %s
#       WHEN `id` = %s THEN %s
#     END
# WHERE `id` IN (%s, %s, %s)
```

### Chunked Batch UPDATE

Process large updates in chunks to reduce lock time.

```python
def chunked_update(table: str, updates: list[dict], key: str, chunk_size: int = 500):
    """Update records in chunks to minimize database locks."""
    total_updated = 0
    
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i + chunk_size]
        query = Q.update(table).batch_update(chunk, key=key)
        sql, params = query.build()
        
        # cursor.execute(sql, params)
        # total_updated += cursor.rowcount
        total_updated += len(chunk)
    
    return total_updated

# Usage
updates = [{"id": i, "processed": True} for i in range(1, 10001)]
chunked_update("records", updates, key="id", chunk_size=1000)
```

### Incremental Batch UPDATE with LIMIT

Update in batches using LIMIT to process subsets.

```python
def incremental_update(batch_size: int = 1000):
    """Update records in batches until all are processed."""
    total_updated = 0
    
    while True:
        query = (
            Q.update("users")
            .set({"migrated": True, "migrated_at": "NOW()"})
            .where("migrated", False)
            .where("created_at <", "2024-01-01")
            .limit(batch_size)
        )
        
        sql, params = query.build()
        # cursor.execute(sql, params)
        # affected = cursor.rowcount
        affected = batch_size  # Simulated
        
        total_updated += affected
        
        if affected < batch_size:
            break  # No more rows to update
    
    return total_updated
```

## Batch DELETE

### DELETE with IN Clause

```python
# Delete multiple records
ids_to_delete = [1, 2, 3, 4, 5]

query = (
    Q.delete_from("old_records")
    .where_in("id", ids_to_delete)
)

# DELETE FROM `old_records` WHERE `id` IN (%s, %s, %s, %s, %s)
```

### Chunked DELETE

```python
def chunked_delete(table: str, condition_column: str, values: list, chunk_size: int = 500):
    """Delete records in chunks."""
    total_deleted = 0
    
    for i in range(0, len(values), chunk_size):
        chunk = values[i:i + chunk_size]
        query = Q.delete_from(table).where_in(condition_column, chunk)
        sql, params = query.build()
        
        # cursor.execute(sql, params)
        # total_deleted += cursor.rowcount
        total_deleted += len(chunk)
    
    return total_deleted

# Usage
old_user_ids = list(range(1, 10001))
chunked_delete("users", "id", old_user_ids, chunk_size=1000)
```

### Incremental DELETE with LIMIT

```python
def incremental_delete(batch_size: int = 1000):
    """Delete old records in batches."""
    total_deleted = 0
    
    while True:
        query = (
            Q.delete_from("logs")
            .where("created_at <", "2023-01-01")
            .limit(batch_size)
        )
        
        sql, params = query.build()
        # cursor.execute(sql, params)
        # affected = cursor.rowcount
        affected = batch_size  # Simulated
        
        total_deleted += affected
        
        if affected < batch_size:
            break
    
    return total_deleted
```

## Performance Optimization

### Transaction Management

Wrap batch operations in transactions for better performance and consistency.

```python
# Pseudo-code for transaction management
# with connection.transaction():
#     for chunk in chunks:
#         query = Q.insert_into("users").values(chunk)
#         cursor.execute(*query.build())
#     # Commit happens automatically
```

### Disable Autocommit

```python
# For large batch operations, disable autocommit
# connection.autocommit = False
# try:
#     for batch in batches:
#         query = Q.insert_into("data").values(batch)
#         cursor.execute(*query.build())
#     connection.commit()
# except Exception:
#     connection.rollback()
#     raise
# finally:
#     connection.autocommit = True
```

### Index Considerations

```python
# For bulk inserts, consider temporarily disabling indexes
# MySQL specific:
# ALTER TABLE users DISABLE KEYS;
# -- Perform bulk insert
# ALTER TABLE users ENABLE KEYS;

# Better: Use LOAD DATA INFILE for very large datasets (outside sqlo)
```

### Batch Size Selection

```python
def optimal_batch_size(total_records: int, max_params: int = 16000) -> int:
    """
    Calculate optimal batch size based on database parameter limits.
    
    MySQL typically has max_allowed_packet and prepared statement limits.
    """
    # Assume 3 parameters per record (adjust based on your schema)
    params_per_record = 3
    max_records_per_batch = max_params // params_per_record
    
    # Cap at 1000 for practical reasons
    return min(1000, max_records_per_batch)

# Usage
records = 150000
batch_size = optimal_batch_size(records)
print(f"Processing {records} records in batches of {batch_size}")
```

## Real-World Examples

### Bulk User Import

```python
def import_users_from_csv(csv_data: list[dict], batch_size: int = 500):
    """Import users from CSV in batches with error handling."""
    successful = 0
    failed = 0
    
    for i in range(0, len(csv_data), batch_size):
        chunk = csv_data[i:i + batch_size]
        
        try:
            query = (
                Q.insert_into("users")
                .values(chunk)
                .on_duplicate_key_update({"updated_at": "NOW()"})
            )
            sql, params = query.build()
            
            # cursor.execute(sql, params)
            # successful += cursor.rowcount
            successful += len(chunk)
            
        except Exception as e:
            print(f"Batch {i // batch_size} failed: {e}")
            failed += len(chunk)
    
    return {"successful": successful, "failed": failed}
```

### Batch Status Update

```python
def update_order_status(order_ids: list[int], new_status: str, batch_size: int = 100):
    """Update order status in batches with audit trail."""
    for i in range(0, len(order_ids), batch_size):
        chunk = order_ids[i:i + batch_size]
        
        # Update orders
        query = (
            Q.update("orders")
            .set({
                "status": new_status,
                "updated_at": "NOW()"
            })
            .where_in("id", chunk)
        )
        # cursor.execute(*query.build())
        
        # Insert audit log
        audit_records = [
            {
                "order_id": order_id,
                "old_status": "pending",  # Would come from SELECT
                "new_status": new_status,
                "changed_at": "NOW()"
            }
            for order_id in chunk
        ]
        
        audit_query = Q.insert_into("order_audit").values(audit_records)
        # cursor.execute(*audit_query.build())
```

### Data Migration

```python
def migrate_legacy_data(batch_size: int = 1000):
    """Migrate data from legacy table to new schema."""
    offset = 0
    total_migrated = 0
    
    while True:
        # Fetch batch from legacy table
        select_query = (
            Q.select("*")
            .from_("legacy_users")
            .limit(batch_size)
            .offset(offset)
        )
        
        # In real code: fetch rows
        # rows = cursor.fetchall()
        # if not rows:
        #     break
        
        # Transform data
        transformed = [
            {
                "user_id": row["id"],
                "full_name": f"{row['first_name']} {row['last_name']}",
                "email": row["email_address"],
                "created_at": row["signup_date"]
            }
            # for row in rows
        ]
        
        # Insert into new table
        insert_query = Q.insert_into("users").values(transformed)
        # cursor.execute(*insert_query.build())
        
        total_migrated += len(transformed)
        offset += batch_size
        
        # if len(rows) < batch_size:
        #     break
    
    return total_migrated
```

### Bulk Cleanup

```python
def cleanup_old_records(table: str, date_column: str, cutoff_date: str, batch_size: int = 500):
    """Delete old records in batches with progress tracking."""
    total_deleted = 0
    batch_number = 0
    
    while True:
        query = (
            Q.delete_from(table)
            .where(f"{date_column} <", cutoff_date)
            .limit(batch_size)
        )
        
        sql, params = query.build()
        # cursor.execute(sql, params)
        # affected = cursor.rowcount
        affected = batch_size  # Simulated
        
        total_deleted += affected
        batch_number += 1
        
        print(f"Batch {batch_number}: Deleted {affected} records (Total: {total_deleted})")
        
        if affected < batch_size:
            break
        
        # Optional: Small delay to reduce load
        # import time
        # time.sleep(0.1)
    
    return total_deleted
```

## Best Practices

### 1. Use Appropriate Batch Sizes

```python
# ✅ Good: Reasonable batch size
batch_size = 500

# ❌ Too small: Too many round trips
batch_size = 10

# ❌ Too large: May hit limits or cause locks
batch_size = 50000
```

### 2. Handle Errors Gracefully

```python
def safe_batch_insert(table: str, data: list[dict], batch_size: int = 500):
    """Insert with error handling per batch."""
    results = {"successful": 0, "failed": 0, "errors": []}
    
    for i in range(0, len(data), batch_size):
        chunk = data[i:i + batch_size]
        
        try:
            query = Q.insert_into(table).values(chunk)
            # cursor.execute(*query.build())
            results["successful"] += len(chunk)
        except Exception as e:
            results["failed"] += len(chunk)
            results["errors"].append({
                "batch": i // batch_size,
                "error": str(e)
            })
    
    return results
```

### 3. Monitor Progress

```python
def batch_with_progress(data: list, batch_size: int = 500):
    """Process batches with progress reporting."""
    total = len(data)
    processed = 0
    
    for i in range(0, total, batch_size):
        chunk = data[i:i + batch_size]
        
        # Process chunk
        query = Q.insert_into("table").values(chunk)
        # cursor.execute(*query.build())
        
        processed += len(chunk)
        progress = (processed / total) * 100
        print(f"Progress: {progress:.1f}% ({processed}/{total})")
```

### 4. Use Prepared Statements

Sqlo automatically uses parameterized queries, which is efficient for batch operations.

```python
# ✅ Automatically parameterized (safe and efficient)
query = Q.insert_into("users").values(data)
sql, params = query.build()
```

## See Also

- [INSERT Queries](insert.md) - INSERT operations
- [UPDATE Queries](update.md) - UPDATE operations including batch_update
- [DELETE Queries](delete.md) - DELETE operations
- [Security Guide](security.md) - Safe batch operations
