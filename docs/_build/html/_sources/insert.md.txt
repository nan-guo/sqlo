# INSERT Queries

Complete guide to INSERT query building with sqlo.

## Basic INSERT

### Single Row Insert

```python
from sqlo import Q

# Insert a single row
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com", "age": 25}
])

sql, params = query.build()
# INSERT INTO `users` (`name`, `email`, `age`) VALUES (%s, %s, %s)
# Params: ('Alice', 'alice@example.com', 25)
```

### Batch Insert

```python
# Insert multiple rows
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com", "age": 25},
    {"name": "Bob", "email": "bob@example.com", "age": 30},
    {"name": "Charlie", "email": "charlie@example.com", "age": 35}
])

sql, params = query.build()
# INSERT INTO `users` (`name`, `email`, `age`) VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s)
# Params: ('Alice', 'alice@example.com', 25, 'Bob', 'bob@example.com', 30, 'Charlie', 'charlie@example.com', 35)
```

## Column Handling

### Explicit Column Order

The library automatically handles column ordering based on the first row:

```python
query = Q.insert_into("users").values([
    {"email": "alice@example.com", "name": "Alice", "age": 25},
    {"name": "Bob", "age": 30, "email": "bob@example.com"}  # Different order, same columns
])

# Columns are ordered consistently based on first row
# INSERT INTO `users` (`email`, `name`, `age`) VALUES (%s, %s, %s), (%s, %s, %s)
```

### Partial Columns

All rows must have the same columns. Missing columns will cause an error:

```python
# ❌ This will raise an error
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob"}  # Missing 'email' column
])
```

## INSERT IGNORE

Ignore duplicate key errors:

```python
query = Q.insert_into("users").ignore().values([
    {"email": "alice@example.com", "name": "Alice"}
])

sql, params = query.build()
# INSERT IGNORE INTO `users` (`email`, `name`) VALUES (%s, %s)
```

### Use Cases for INSERT IGNORE

```python
# Avoid errors when inserting potentially duplicate records
query = Q.insert_into("user_tags").ignore().values([
    {"user_id": 1, "tag_id": 10},
    {"user_id": 1, "tag_id": 11},
    {"user_id": 1, "tag_id": 10}  # Duplicate, will be ignored
])
```

## ON DUPLICATE KEY UPDATE

Update existing rows when a duplicate key is encountered:

### Basic Usage

```python
query = (
    Q.insert_into("users")
    .values([{"email": "alice@example.com", "name": "Alice", "login_count": 1}])
    .on_duplicate_key_update({"login_count": "login_count + 1"})
)

sql, params = query.build()
# INSERT INTO `users` (`email`, `name`, `login_count`) VALUES (%s, %s, %s)
# ON DUPLICATE KEY UPDATE `login_count` = login_count + 1
```

### Update Multiple Columns

```python
query = (
    Q.insert_into("users")
    .values([{"email": "alice@example.com", "name": "Alice", "last_login": "2023-11-23"}])
    .on_duplicate_key_update({
        "name": "Alice Updated",
        "last_login": "2023-11-23",
        "updated_at": "NOW()"
    })
)

# ON DUPLICATE KEY UPDATE `name` = %s, `last_login` = %s, `updated_at` = NOW()
```

### Using VALUES() Reference

```python
# Reference the value from INSERT
query = (
    Q.insert_into("users")
    .values([{"email": "alice@example.com", "name": "Alice", "login_count": 1}])
    .on_duplicate_key_update({
        "name": "VALUES(name)",  # Use the name from INSERT
        "login_count": "login_count + VALUES(login_count)"
    })
)

# ON DUPLICATE KEY UPDATE `name` = VALUES(name), `login_count` = login_count + VALUES(login_count)
```

## Combining INSERT IGNORE and ON DUPLICATE KEY UPDATE

> [!WARNING]
> You cannot use both `INSERT IGNORE` and `ON DUPLICATE KEY UPDATE` together. They are mutually exclusive.

```python
# ❌ This will raise an error
query = (
    Q.insert_into("users")
    .ignore()
    .values([{"email": "alice@example.com"}])
    .on_duplicate_key_update({"name": "Updated"})
)
```

Choose one based on your needs:
- Use `INSERT IGNORE` when you want to silently skip duplicates
- Use `ON DUPLICATE KEY UPDATE` when you want to update existing rows

## INSERT with Subquery

Insert data from a SELECT query:

```python
# Select data from one table and insert into another
select_query = (
    Q.select("name", "email", "created_at")
    .from_("temp_users")
    .where("verified", True)
)

query = Q.insert_into("users").from_select(
    columns=["name", "email", "created_at"],
    select_query=select_query
)

sql, params = query.build()
# INSERT INTO `users` (`name`, `email`, `created_at`)
# SELECT `name`, `email`, `created_at` FROM `temp_users` WHERE `verified` = %s
```

### With Column Mapping

```python
# Map columns from SELECT to INSERT
select_query = Q.select("full_name", "email_address").from_("import_data")

query = Q.insert_into("users").from_select(
    columns=["name", "email"],  # Target columns
    select_query=select_query    # Source has different column names
)

# INSERT INTO `users` (`name`, `email`)
# SELECT `full_name`, `email_address` FROM `import_data`
```

## Dynamic INSERT Building

### Conditional Values

```python
def create_user(data: dict):
    """Build INSERT query dynamically based on provided data"""
    # Filter out None values
    values = {k: v for k, v in data.items() if v is not None}
    
    query = Q.insert_into("users").values([values])
    return query

# Usage
query = create_user({
    "name": "Alice",
    "email": "alice@example.com",
    "phone": None  # Will be excluded
})
# INSERT INTO `users` (`name`, `email`) VALUES (%s, %s)
```

### Batch Insert with Validation

```python
def batch_insert_users(users: list[dict]):
    """Insert multiple users with validation"""
    if not users:
        raise ValueError("No users to insert")
    
    # Ensure all users have required fields
    required_fields = {"name", "email"}
    for user in users:
        if not required_fields.issubset(user.keys()):
            raise ValueError(f"Missing required fields: {required_fields - user.keys()}")
    
    query = Q.insert_into("users").values(users)
    return query
```

## Advanced Examples

### Upsert Pattern

```python
# Insert or update user profile
def upsert_user_profile(user_id: int, profile_data: dict):
    query = (
        Q.insert_into("user_profiles")
        .values([{
            "user_id": user_id,
            **profile_data,
            "created_at": "NOW()"
        }])
        .on_duplicate_key_update({
            **profile_data,
            "updated_at": "NOW()"
        })
    )
    return query

# Usage
query = upsert_user_profile(123, {
    "bio": "Software developer",
    "location": "San Francisco",
    "website": "https://example.com"
})
```

### Bulk Insert with Chunking

```python
def bulk_insert_chunked(table: str, data: list[dict], chunk_size: int = 1000):
    """Insert large datasets in chunks to avoid query size limits"""
    queries = []
    
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        query = Q.insert_into(table).values(chunk)
        queries.append(query)
    
    return queries

# Usage
large_dataset = [{"name": f"User{i}", "email": f"user{i}@example.com"} for i in range(10000)]
queries = bulk_insert_chunked("users", large_dataset, chunk_size=500)
# Returns 20 queries, each inserting 500 rows
```

### Insert with Default Values

```python
# Add default values to all rows
def insert_with_defaults(table: str, data: list[dict], defaults: dict):
    """Add default values to all rows before inserting"""
    enriched_data = [{**defaults, **row} for row in data]
    return Q.insert_into(table).values(enriched_data)

# Usage
query = insert_with_defaults(
    "users",
    [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"}
    ],
    defaults={
        "active": True,
        "role": "user",
        "created_at": "NOW()"
    }
)
# Each row will have active, role, and created_at fields
```

## Performance Tips

### Batch Inserts

```python
# ✅ Good: Batch insert (single query)
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
])
# 1 query, 3 rows

# ❌ Bad: Individual inserts (multiple queries)
for user in users:
    query = Q.insert_into("users").values([user])
    # Execute...
# 3 queries, 1 row each
```

### Optimal Batch Size

```python
# Balance between query size and number of queries
OPTIMAL_BATCH_SIZE = 1000  # Adjust based on your data and database

def insert_optimized(data: list[dict]):
    if len(data) <= OPTIMAL_BATCH_SIZE:
        return [Q.insert_into("users").values(data)]
    
    # Split into chunks
    return bulk_insert_chunked("users", data, OPTIMAL_BATCH_SIZE)
```

### Use Transactions

```python
# When inserting multiple batches, use transactions
# (Note: Transaction handling is done at the database connection level)

# Example with your database library:
# with connection.transaction():
#     for query in queries:
#         sql, params = query.build()
#         cursor.execute(sql, params)
```

## Common Patterns

### Insert and Get ID

```python
# Build the query
query = Q.insert_into("users").values([
    {"name": "Alice", "email": "alice@example.com"}
])

sql, params = query.build()

# Execute and get last insert ID (database-specific)
# cursor.execute(sql, params)
# user_id = cursor.lastrowid  # MySQL/SQLite
```

### Insert with Timestamp

```python
from datetime import datetime

query = Q.insert_into("posts").values([{
    "title": "My Post",
    "content": "Post content",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}])
```

### Insert with JSON Data

```python
import json

query = Q.insert_into("settings").values([{
    "user_id": 123,
    "preferences": json.dumps({"theme": "dark", "language": "en"}),
    "created_at": "NOW()"
}])
```

## Error Handling

### Validation Before Insert

```python
def safe_insert(table: str, data: list[dict]):
    """Validate data before building INSERT query"""
    if not data:
        raise ValueError("Cannot insert empty data")
    
    if not isinstance(data, list):
        raise TypeError("Data must be a list of dictionaries")
    
    # Check all rows have same columns
    first_keys = set(data[0].keys())
    for i, row in enumerate(data[1:], start=1):
        if set(row.keys()) != first_keys:
            raise ValueError(f"Row {i} has different columns than row 0")
    
    return Q.insert_into(table).values(data)
```

## See Also

- [UPDATE Queries](update.md) - Updating existing data
- [SELECT Queries](select.md) - Querying data
- [Getting Started](getting-started.md) - Basic concepts
