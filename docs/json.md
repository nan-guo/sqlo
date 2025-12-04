# JSON Support

Complete guide to working with JSON columns in sqlo.

## Introduction

sqlo provides native support for querying and manipulating JSON columns in MySQL. The `JSON` class allows you to extract, filter, and update JSON data using MySQL's JSON functions.

## JSON Path Extraction

Use the `JSON` class to extract values from JSON columns.

```python
from sqlo import Q, JSON

# Extract a JSON field in SELECT
query = Q.select(
    "id",
    JSON("data").extract("name").as_("user_name"),
    JSON("data").extract("age").as_("user_age")
).from_("users")

sql, params = query.build()
# SELECT `id`,
#   `data`->>'$.name' AS `user_name`,
#   `data`->>'$.age' AS `user_age`
# FROM `users`
```

## JSON Path Syntax

JSON paths follow MySQL's JSON path syntax:
- `$.field` - Top-level field
- `$.field.nested` - Nested field
- `$.array[0]` - Array element
- `$.field[*]` - All array elements

```python
# Top-level field
JSON("profile").extract("email")
# SQL: `profile`->>'$.email'

# Nested field
JSON("data").extract("address.city")
# SQL: `data`->>'$.address.city'

# Array element
JSON("tags").extract("[0]")
# SQL: `tags`->>'$[0]'

# Nested array
JSON("data").extract("items[0].name")
# SQL: `data`->>'$.items[0].name'
```

## Filtering by JSON Values

### Simple Equality

```python
# WHERE JSON field equals value
query = (
    Q.select("*")
    .from_("users")
    .where(JSON("preferences").extract("theme"), "dark")
)
# WHERE `preferences`->>'$.theme' = %s
```

### Comparison Operators

```python
# Numeric comparisons
query = (
    Q.select("*")
    .from_("users")
    .where(JSON("data").extract("age"), 18, ">")
)
# WHERE `data`->>'$.age' > %s

# Multiple conditions
query = (
    Q.select("*")
    .from_("products")
    .where(JSON("specs").extract("weight"), 100, "<")
    .where(JSON("specs").extract("price"), 1000, "<=")
)
```

### NULL Checks

```python
# Check if JSON field is NULL or missing
query = (
    Q.select("*")
    .from_("users")
    .where_null(JSON("data").extract("phone"))
)
# WHERE `data`->>'$.phone' IS NULL

# Check if JSON field exists and is not NULL
query = (
    Q.select("*")
    .from_("users")
    .where_not_null(JSON("profile").extract("verified_at"))
)
```

### Pattern Matching

```python
# LIKE with JSON values
query = (
    Q.select("*")
    .from_("users")
    .where_like(JSON("data").extract("email"), "%@example.com")
)
# WHERE `data`->>'$.email' LIKE %s
```

## JSON Functions

### JSON_CONTAINS

Check if a JSON document contains a specific value.

```python
from sqlo import Raw, func

# Check if array contains value
query = (
    Q.select("*")
    .from_("users")
    .where(Raw("JSON_CONTAINS(tags, '\"premium\"')"))
)
```

### JSON_ARRAY_LENGTH

Get the length of a JSON array.

```python
# Users with more than 5 tags
query = (
    Q.select("id", "name", Raw("JSON_LENGTH(tags)").as_("tag_count"))
    .from_("users")
    .where(Raw("JSON_LENGTH(tags) > 5"))
)
```

### JSON_KEYS

Extract all keys from a JSON object.

```python
# Get all keys from JSON object
query = Q.select(
    "id",
    Raw("JSON_KEYS(data)").as_("available_fields")
).from_("users")
```

## Updating JSON Columns

### Replace Entire JSON

```python
import json

# Update entire JSON column
data = {"name": "Alice", "age": 30, "city": "Paris"}

query = (
    Q.update("users")
    .set({"profile": json.dumps(data)})
    .where("id", 123)
)
```

### JSON_SET - Update Specific Fields

```python
# Update a specific JSON field
query = (
    Q.update("users")
    .set({
        "data": Raw("JSON_SET(data, '$.last_login', NOW())")
    })
    .where("id", 123)
)

# Update multiple JSON fields
query = (
    Q.update("users")
    .set({
        "profile": Raw(
            "JSON_SET(profile, '$.name', %s, '$.age', %s)",
            ["Alice", 30]
        )
    })
    .where("id", 123)
)
```

### JSON_INSERT - Add New Fields

```python
# Add field only if it doesn't exist
query = (
    Q.update("users")
    .set({
        "data": Raw("JSON_INSERT(data, '$.created_at', NOW())")
    })
    .where_null(JSON("data").extract("created_at"))
)
```

### JSON_REMOVE - Delete Fields

```python
# Remove a field from JSON
query = (
    Q.update("users")
    .set({
        "data": Raw("JSON_REMOVE(data, '$.temporary_field')")
    })
    .where_not_null(JSON("data").extract("temporary_field"))
)
```

### JSON_ARRAY_APPEND - Add to Array

```python
# Append to JSON array
query = (
    Q.update("users")
    .set({
        "tags": Raw("JSON_ARRAY_APPEND(tags, '$', %s)", ["new_tag"])
    })
    .where("id", 123)
)
```

## Inserting JSON Data

```python
import json

# Insert with JSON data
user_data = {
    "name": "Bob",
    "email": "bob@example.com",
    "preferences": {
        "theme": "dark",
        "language": "en",
        "notifications": True
    }
}

query = Q.insert_into("users").values([{
    "username": "bob",
    "profile": json.dumps(user_data)
}])

# Or use Raw for JSON functions
query = Q.insert_into("users").values([{
    "username": "alice",
    "profile": Raw("JSON_OBJECT('name', %s, 'email', %s)", ["Alice", "alice@example.com"])
}])
```

## Complex JSON Queries

### Joining on JSON Values

```python
# Join tables using JSON field
query = (
    Q.select("u.id", "u.name", "o.total")
    .from_("users u")
    .join(
        "orders o",
        Raw("o.customer_id = u.data->>'$.customer_id'")
    )
)
```

### Aggregating JSON Values

```python
# Count users by preference
query = (
    Q.select(
        JSON("preferences").extract("theme").as_("theme"),
        func.count("*").as_("user_count")
    )
    .from_("users")
    .group_by(JSON("preferences").extract("theme"))
)
```

### Subqueries with JSON

```python
# Find users with specific nested values
subquery = (
    Q.select("id")
    .from_("users")
    .where(JSON("data").extract("address.country"), "France")
)

query = (
    Q.select("*")
    .from_("orders")
    .where_in("user_id", subquery)
)
```

## Common Patterns

### User Preferences

```python
# Get users with specific preferences
query = (
    Q.select("id", "username", JSON("preferences").extract("theme"))
    .from_("users")
    .where(JSON("preferences").extract("notifications"), True)
    .where(JSON("preferences").extract("language"), "fr")
)
```

### Dynamic Attributes

```python
# Products with flexible attributes
query = (
    Q.select(
        "id",
        "name",
        JSON("attributes").extract("color").as_("color"),
        JSON("attributes").extract("size").as_("size"),
        JSON("attributes").extract("material").as_("material")
    )
    .from_("products")
    .where(JSON("attributes").extract("color"), "red")
)
```

### Event Logging

```python
# Query event logs
query = (
    Q.select(
        "id",
        JSON("event_data").extract("user_id"),
        JSON("event_data").extract("action"),
        "created_at"
    )
    .from_("event_logs")
    .where(JSON("event_data").extract("action"), "login")
    .where("created_at >", "2024-01-01")
)
```

### Settings Management

```python
# Update user settings
query = (
    Q.update("users")
    .set({
        "settings": Raw(
            "JSON_SET(settings, '$.email_notifications', %s, '$.sms_notifications', %s)",
            [True, False]
        )
    })
    .where("id", 123)
)
```

## Performance Considerations

### Generated Columns

For frequently queried JSON fields, consider creating generated columns with indexes:

```sql
-- Create a generated column from JSON
ALTER TABLE users
ADD COLUMN email_from_json VARCHAR(255)
AS (data->>'$.email') STORED;

-- Add index
CREATE INDEX idx_email ON users(email_from_json);
```

Then query directly:
```python
# Faster than JSON extraction
query = Q.select("*").from_("users").where("email_from_json", "alice@example.com")
```

### JSON vs Normalized Tables

```python
# ❌ Avoid: Complex queries on deeply nested JSON
query = Q.select("*").from_("users").where(
    JSON("data").extract("orders[0].items[0].category"), "electronics"
)

# ✅ Better: Normalize frequently queried data
query = Q.select("u.*").from_("users u") \
    .join("orders o", "o.user_id = u.id") \
    .join("order_items oi", "oi.order_id = o.id") \
    .where("oi.category", "electronics")
```

### Limit JSON Column Size

```python
# Keep JSON columns manageable
# ❌ Bad: Huge nested structures
# ✅ Good: Specific, bounded data
user_preferences = {
    "theme": "dark",
    "language": "en",
    "notifications": True
}
```

## Safety Notes

### SQL Injection Prevention

```python
# ✅ Safe: Use parameters
value = user_input
query = Q.select("*").from_("users").where(JSON("data").extract("name"), value)

# ❌ Dangerous: String interpolation
query = Q.select("*").from_("users").where(Raw(f"data->>'$.name' = '{user_input}'"))
```

### Validate JSON Before Insert

```python
import json

def safe_json_insert(data_dict):
    try:
        # Validate JSON
        json_str = json.dumps(data_dict)
        json.loads(json_str)  # Verify it's valid
        
        return Q.insert_into("users").values([{"data": json_str}])
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid JSON data: {e}")
```

## See Also

- [SELECT Queries](select.md) - Using JSON in SELECT
- [UPDATE Queries](update.md) - Updating JSON columns
- [INSERT Queries](insert.md) - Inserting JSON data
- [Expressions & Functions](expressions.md) - Custom functions with JSON
