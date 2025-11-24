# SELECT Queries

Complete guide to SELECT query building with dm-core-sql-toolkit.

## Basic Queries

### Simple SELECT

```python
from sqlo import Q

# Select all columns
query = Q.select("*").from_("users")
sql, params = query.build()
# SELECT * FROM `users`

# Select specific columns
query = Q.select("id", "name", "email").from_("users")
sql, params = query.build()
# SELECT `id`, `name`, `email` FROM `users`
```

### Table Aliases

```python
query = Q.select("u.id", "u.name").from_("users AS u")
sql, params = query.build()
# SELECT `u`.`id`, `u`.`name` FROM `users` AS `u`
```

## WHERE Clauses

### Basic Conditions

```python
# Simple equality
query = Q.select("*").from_("users").where("active", True)
# WHERE `active` = ?

# Comparison operators (Standard)
query = Q.select("*").from_("users").where("age >", 18)
# WHERE `age` > ?

# Compact Syntax (New)
query = Q.select("*").from_("users").where("age>", 18)
# WHERE `age` > ?

query = Q.select("*").from_("users").where("age>=", 18)
# WHERE `age` >= ?

# Extended Operators
query = Q.select("*").from_("users").where("name LIKE", "John%")
# WHERE `name` LIKE ?

query = Q.select("*").from_("users").where("created_at >=", "2023-01-01")
# WHERE `created_at` >= ?
```

### Multiple Conditions

```python
# AND conditions (default)
query = (
    Q.select("*")
    .from_("users")
    .where("active", True)
    .where("age >=", 18)
)
# WHERE `active` = ? AND `age` >= ?

# OR conditions
query = (
    Q.select("*")
    .from_("users")
    .or_where("role", "admin")
    .or_where("role", "moderator")
)
# WHERE `role` = ? OR `role` = ?
```

### IN and NOT IN

```python
# IN clause
query = Q.select("*").from_("users").where_in("id", [1, 2, 3, 4, 5])
# WHERE `id` IN (?, ?, ?, ?, ?)

# NOT IN clause
query = Q.select("*").from_("users").where_not_in("status", ["banned", "deleted"])
# WHERE `status` NOT IN (?, ?)
```

### NULL Checks

```python
# IS NULL
query = Q.select("*").from_("users").where_null("deleted_at")
# WHERE `deleted_at` IS NULL

# IS NOT NULL
query = Q.select("*").from_("users").where_not_null("email_verified_at")
# WHERE `email_verified_at` IS NOT NULL
```

### BETWEEN

```python
query = Q.select("*").from_("orders").where_between("created_at", "2023-01-01", "2023-12-31")
# WHERE `created_at` BETWEEN ? AND ?

query = Q.select("*").from_("products").where_not_between("price", 10, 100)
# WHERE `price` NOT BETWEEN ? AND ?
```

### LIKE Patterns

```python
# LIKE
query = Q.select("*").from_("users").where_like("email", "%@example.com")
# WHERE `email` LIKE ?

# NOT LIKE
query = Q.select("*").from_("users").where_not_like("name", "test%")
# WHERE `name` NOT LIKE ?
```

## Complex Conditions

### Using Condition Objects

```python
from sqlo import Condition

# Create complex conditions
condition = Condition.and_(
    Condition("age", ">=", 18),
    Condition.or_(
        Condition("country", "=", "US"),
        Condition("country", "=", "CA")
    )
)

query = Q.select("*").from_("users").where(condition)
# WHERE (`age` >= ? AND (`country` = ? OR `country` = ?))
```

See [Condition Objects](conditions.md) for detailed information.

## ORDER BY

### Basic Sorting

```python
# Ascending order
query = Q.select("*").from_("users").order_by("name")
# ORDER BY `name` ASC

# Descending order (prefix with -)
query = Q.select("*").from_("users").order_by("-created_at")
# ORDER BY `created_at` DESC

# Multiple columns
query = Q.select("*").from_("users").order_by("country", "-created_at", "name")
# ORDER BY `country` ASC, `created_at` DESC, `name` ASC
```

### Raw SQL in ORDER BY

```python
from sqlo import Raw

query = Q.select("*").from_("products").order_by(Raw("FIELD(status, 'active', 'pending', 'inactive')"))
# ORDER BY FIELD(status, 'active', 'pending', 'inactive')
```

## LIMIT and OFFSET

### Pagination

```python
# LIMIT only
query = Q.select("*").from_("users").limit(10)
# LIMIT 10

# LIMIT with OFFSET
query = Q.select("*").from_("users").limit(10).offset(20)
# LIMIT 10 OFFSET 20

# Helper method for pagination
query = Q.select("*").from_("users").paginate(page=3, per_page=20)
# LIMIT 20 OFFSET 40
```

## GROUP BY and HAVING

### Grouping

```python
query = (
    Q.select("country", "COUNT(*) as user_count")
    .from_("users")
    .group_by("country")
)
# SELECT `country`, COUNT(*) as user_count FROM `users` GROUP BY `country`

# Multiple columns
query = (
    Q.select("country", "city", "COUNT(*) as count")
    .from_("users")
    .group_by("country", "city")
)
# GROUP BY `country`, `city`
```

### HAVING Clause

```python
query = (
    Q.select("country", "COUNT(*) as user_count")
    .from_("users")
    .group_by("country")
    .having("COUNT(*) >", 100)
)
# HAVING COUNT(*) > ?

# Multiple HAVING conditions
query = (
    Q.select("country", "AVG(age) as avg_age")
    .from_("users")
    .group_by("country")
    .having("AVG(age) >=", 18)
    .having("COUNT(*) >", 50)
)
# HAVING AVG(age) >= ? AND COUNT(*) > ?
```

## DISTINCT

```python
query = Q.select("country").from_("users").distinct()
# SELECT DISTINCT `country` FROM `users`

# DISTINCT with multiple columns
query = Q.select("country", "city").from_("users").distinct()
# SELECT DISTINCT `country`, `city` FROM `users`
```

## UNION

### Basic UNION

```python
query1 = Q.select("id", "name").from_("active_users")
query2 = Q.select("id", "name").from_("inactive_users")

combined = query1.union(query2)
sql, params = combined.build()
# SELECT `id`, `name` FROM `active_users`
# UNION
# SELECT `id`, `name` FROM `inactive_users`
```

### UNION ALL

```python
query1 = Q.select("id", "name").from_("users_2022")
query2 = Q.select("id", "name").from_("users_2023")

combined = query1.union_all(query2)
# UNION ALL (includes duplicates)
```

### Multiple UNION

```python
q1 = Q.select("id", "name").from_("table1")
q2 = Q.select("id", "name").from_("table2")
q3 = Q.select("id", "name").from_("table3")

combined = q1.union(q2).union(q3)
# Multiple UNION operations
```

## Subqueries

### Subquery in WHERE

```python
subquery = Q.select("user_id").from_("orders").where("total >", 1000)

query = (
    Q.select("*")
    .from_("users")
    .where_in("id", subquery)
)
# WHERE `id` IN (SELECT `user_id` FROM `orders` WHERE `total` > ?)
```

### Subquery in FROM

```python
subquery = (
    Q.select("user_id", "COUNT(*) as order_count")
    .from_("orders")
    .group_by("user_id")
)

query = (
    Q.select("u.name", "o.order_count")
    .from_(subquery.as_("o"))
    .join("users AS u", "u.id = o.user_id")
)
# SELECT `u`.`name`, `o`.`order_count`
# FROM (SELECT `user_id`, COUNT(*) as order_count FROM `orders` GROUP BY `user_id`) AS `o`
# INNER JOIN `users` AS `u` ON u.id = o.user_id
```

### Scalar Subquery in SELECT

```python
subquery = (
    Q.select("COUNT(*)")
    .from_("orders")
    .where("orders.user_id = users.id")
)

query = (
    Q.select("id", "name", subquery.as_("order_count"))
    .from_("users")
)
# SELECT `id`, `name`, (SELECT COUNT(*) FROM `orders` WHERE orders.user_id = users.id) AS `order_count`
# FROM `users`
```

## Index Hints

### FORCE INDEX

```python
query = Q.select("*").from_("users").force_index("idx_email")
# SELECT * FROM `users` FORCE INDEX (`idx_email`)

# Multiple indexes
query = Q.select("*").from_("users").force_index("idx_email", "idx_created_at")
# FORCE INDEX (`idx_email`, `idx_created_at`)
```

### USE INDEX

```python
query = Q.select("*").from_("users").use_index("idx_name")
# SELECT * FROM `users` USE INDEX (`idx_name`)
```

### IGNORE INDEX

```python
query = Q.select("*").from_("users").ignore_index("idx_old")
# SELECT * FROM `users` IGNORE INDEX (`idx_old`)
```

## Dynamic Query Building

### Conditional Clauses with `when()`

```python
def build_user_query(filters: dict):
    query = Q.select("*").from_("users")
    
    # Add WHERE clause only if filter exists
    query = query.when(
        "email" in filters,
        lambda q: q.where("email", filters["email"])
    )
    
    query = query.when(
        "min_age" in filters,
        lambda q: q.where("age >=", filters["min_age"])
    )
    
    return query

# Usage
query = build_user_query({"email": "test@example.com"})
# Only includes WHERE email = ?

query = build_user_query({"min_age": 18})
# Only includes WHERE age >= ?
```

### Complex Dynamic Conditions

```python
def search_products(name=None, min_price=None, max_price=None, categories=None):
    query = Q.select("*").from_("products")
    
    query = (
        query
        .when(name, lambda q: q.where_like("name", f"%{name}%"))
        .when(min_price, lambda q: q.where("price >=", min_price))
        .when(max_price, lambda q: q.where("price <=", max_price))
        .when(categories, lambda q: q.where_in("category_id", categories))
    )
    
    return query
```

## Advanced Examples

### Complex Query with Multiple Features

```python
query = (
    Q.select(
        "u.id",
        "u.name",
        "u.email",
        "COUNT(o.id) as order_count",
        "SUM(o.total) as total_spent"
    )
    .from_("users AS u")
    .left_join("orders AS o", "o.user_id = u.id")
    .where("u.active", True)
    .where("u.created_at >=", "2023-01-01")
    .group_by("u.id", "u.name", "u.email")
    .having("COUNT(o.id) >", 0)
    .order_by("-total_spent", "u.name")
    .limit(100)
)
```

### Pagination with Total Count

```python
# Get paginated results
query = (
    Q.select("*")
    .from_("users")
    .where("active", True)
    .order_by("-created_at")
    .paginate(page=1, per_page=20)
)

# Get total count (without LIMIT)
count_query = (
    Q.select("COUNT(*) as total")
    .from_("users")
    .where("active", True)
)
```

## Performance Tips

1. **Use specific columns** instead of `SELECT *` when possible
2. **Add appropriate indexes** for WHERE and JOIN columns
3. **Use LIMIT** to restrict result sets
4. **Use EXPLAIN** to analyze query performance (see below)
5. **Avoid N+1 queries** by using JOINs or subqueries

### EXPLAIN Support

```python
query = Q.select("*").from_("users").where("email", "test@example.com")
explain_query = query.explain()
explain_sql, params = explain_query.build()
# Returns: EXPLAIN SELECT * FROM `users` WHERE `email` = ?

# Execute with your database connection to see query plan
# cursor.execute(explain_sql, params)
```

## See Also

- [JOIN Operations](joins.md) - Detailed JOIN documentation
- [Condition Objects](conditions.md) - Complex condition building
- [Expressions & Functions](expressions.md) - SQL functions and raw expressions
- [Getting Started](getting-started.md) - Basic concepts
