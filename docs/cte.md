# Common Table Expressions (CTE)

Complete guide to using CTEs with sqlo.

## Introduction

Common Table Expressions (CTEs) are temporary named result sets that exist only during query execution. They make complex queries more readable and maintainable by breaking them into logical, reusable parts.

## Basic Syntax

Use the `with_()` method to define CTEs before your main query.

```python
from sqlo import Q, func

# Define a CTE
cte = Q.select("user_id", func.count("*").as_("order_count")) \
    .from_("orders") \
    .group_by("user_id") \
    .as_("user_orders")

# Use it in main query
query = (
    Q.select("u.name", "uo.order_count")
    .with_(cte)
    .from_("users", alias="u")
    .join("user_orders uo", "u.id = uo.user_id")
)

sql, params = query.build()
# WITH `user_orders` AS (
#   SELECT `user_id`, COUNT(*) AS `order_count` FROM `orders` GROUP BY `user_id`
# )
# SELECT `u`.`name`, `uo`.`order_count`
# FROM `users` AS `u`
# INNER JOIN `user_orders` `uo` ON u.id = uo.user_id
```

## Naming CTEs

Every CTE must have a name using the `as_()` method.

```python
# ✅ Correct: Named CTE
cte = Q.select("*").from_("users").where("active", True).as_("active_users")

# ❌ Error: CTE without name
try:
    cte = Q.select("*").from_("users").where("active", True)
    query = Q.select("*").with_(cte).from_("active_users")
except ValueError as e:
    print(e)  # "CTE must have a name. Use .as_('name') method."
```

## Multiple CTEs

You can define multiple CTEs in a single query.

```python
# Define multiple CTEs
high_value_orders = (
    Q.select("user_id", func.sum("total").as_("total_spent"))
    .from_("orders")
    .where("total >", 1000)
    .group_by("user_id")
    .as_("high_value")
)

recent_users = (
    Q.select("id", "name", "email")
    .from_("users")
    .where("created_at >", "2024-01-01")
    .as_("recent")
)

# Use both CTEs
query = (
    Q.select("r.name", "r.email", "h.total_spent")
    .with_(high_value_orders)
    .with_(recent_users)
    .from_("recent r")
    .left_join("high_value h", "h.user_id = r.id")
)

# WITH `high_value` AS (...),
#      `recent` AS (...)
# SELECT ...
```

## Recursive CTEs

Recursive CTEs reference themselves and are useful for hierarchical or graph data.

```python
# Employee hierarchy: Find all subordinates
recursive_cte = (
    Q.select("id", "name", "manager_id", Raw("1").as_("level"))
    .from_("employees")
    .where("id", 1)  # Start with CEO
    .union_all(
        Q.select("e.id", "e.name", "e.manager_id", Raw("cte.level + 1"))
        .from_("employees e")
        .join("employee_hierarchy cte", "e.manager_id = cte.id")
    )
    .as_("employee_hierarchy")
)

query = (
    Q.select("*")
    .with_(recursive_cte)
    .from_("employee_hierarchy")
    .order_by("level", "name")
)

# WITH RECURSIVE `employee_hierarchy` AS (
#   SELECT `id`, `name`, `manager_id`, 1 AS `level`
#   FROM `employees` WHERE `id` = %s
#   UNION ALL
#   SELECT `e`.`id`, `e`.`name`, `e`.`manager_id`, cte.level + 1
#   FROM `employees` `e`
#   INNER JOIN `employee_hierarchy` `cte` ON e.manager_id = cte.id
# )
# SELECT * FROM `employee_hierarchy` ORDER BY `level` ASC, `name` ASC
```

## CTEs with Different Query Types

CTEs can be used with SELECT, INSERT, UPDATE, and DELETE queries.

### CTE with INSERT

```python
# Insert top performers into a rewards table
top_sellers = (
    Q.select("salesperson_id", func.sum("amount").as_("total"))
    .from_("sales")
    .where("year", 2024)
    .group_by("salesperson_id")
    .having("SUM(amount) >", 100000)
    .as_("top_sellers")
)

query = (
    Q.insert_into("rewards")
    .with_(top_sellers)
    .values([{
        "salesperson_id": Raw("ts.salesperson_id"),
        "reward_type": "top_performer",
        "year": 2024
    }])
    .from_("top_sellers ts")
)
```

### CTE with UPDATE

```python
# Update users based on aggregated order data
order_summary = (
    Q.select("user_id", func.count("*").as_("order_count"))
    .from_("orders")
    .group_by("user_id")
    .as_("summary")
)

query = (
    Q.update("users u")
    .with_(order_summary)
    .join("summary s", "s.user_id = u.id")
    .set({"u.total_orders": Raw("s.order_count")})
    .where("s.order_count >", 0)
)
```

### CTE with DELETE

```python
# Delete inactive users with no recent orders
inactive_users = (
    Q.select("u.id")
    .from_("users u")
    .left_join("orders o", "o.user_id = u.id AND o.created_at > DATE_SUB(NOW(), INTERVAL 1 YEAR)")
    .where_null("o.id")
    .where("u.last_login <", "2023-01-01")
    .as_("to_delete")
)

query = (
    Q.delete_from("users")
    .with_(inactive_users)
    .where_in("id", Q.select("id").from_("to_delete"))
)
```

## Common Use Cases

### Data Aggregation Pipeline

```python
# Multi-step aggregation
monthly_sales = (
    Q.select(
        Raw("DATE_FORMAT(created_at, '%Y-%m')").as_("month"),
        "product_id",
        func.sum("amount").as_("total")
    )
    .from_("sales")
    .group_by(Raw("DATE_FORMAT(created_at, '%Y-%m')"), "product_id")
    .as_("monthly")
)

product_ranking = (
    Q.select(
        "month",
        "product_id",
        "total",
        func.row_number().over(
            Window.partition_by("month").and_order_by("-total")
        ).as_("rank")
    )
    .with_(monthly_sales)
    .from_("monthly")
    .as_("ranked")
)

query = (
    Q.select("r.month", "p.name", "r.total", "r.rank")
    .with_(product_ranking)
    .from_("ranked r")
    .join("products p", "p.id = r.product_id")
    .where("r.rank <=", 10)
)
```

### Deduplication

```python
# Find and keep only the latest record for each user
duplicates = (
    Q.select(
        "id",
        func.row_number().over(
            Window.partition_by("email").and_order_by("-created_at")
        ).as_("rn")
    )
    .from_("users")
    .as_("ranked")
)

query = (
    Q.delete_from("users")
    .with_(duplicates)
    .where_in("id",
        Q.select("id").from_("ranked").where("rn >", 1)
    )
)
```

### Date Series Generation

```python
# Generate a series of dates
from sqlo import Raw

# Note: MySQL requires a numbers table or recursive CTE for date series
date_range = (
    Q.select(Raw("DATE_ADD('2024-01-01', INTERVAL n DAY)").as_("date"))
    .from_("(SELECT 0 as n UNION ALL SELECT 1 UNION ALL SELECT 2 /* ... */) numbers")
    .where(Raw("n < DATEDIFF('2024-12-31', '2024-01-01')"))
    .as_("dates")
)

# Join with sales data to include days with zero sales
query = (
    Q.select(
        "d.date",
        func.coalesce(func.sum("s.amount"), 0).as_("total")
    )
    .with_(date_range)
    .from_("dates d")
    .left_join("sales s", "DATE(s.created_at) = d.date")
    .group_by("d.date")
)
```

### Running Calculations

```python
# Calculate cumulative values using CTE
daily_sales = (
    Q.select(
        Raw("DATE(created_at)").as_("date"),
        func.sum("amount").as_("daily_total")
    )
    .from_("sales")
    .group_by(Raw("DATE(created_at)"))
    .as_("daily")
)

query = (
    Q.select(
        "date",
        "daily_total",
        func.sum("daily_total").over(
            Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
        ).as_("running_total")
    )
    .with_(daily_sales)
    .from_("daily")
    .order_by("date")
)
```

## Performance Considerations

### Materialization

CTEs are typically materialized (executed once and stored), which can be beneficial or detrimental depending on the use case.

```python
# ✅ Good: CTE reduces redundant calculations
expensive_calc = (
    Q.select(
        "user_id",
        Raw("COMPLEX_CALCULATION(data)").as_("result")
    )
    .from_("large_table")
    .as_("calc")
)

query = (
    Q.select("*")
    .with_(expensive_calc)
    .from_("calc")
    .where("result >", 100)
)
```

### Indexes

Ensure base tables in CTEs have appropriate indexes.

```python
# Make sure 'created_at' is indexed
recent_orders = (
    Q.select("user_id", "total")
    .from_("orders")
    .where("created_at >", "2024-01-01")  # Uses index
    .as_("recent")
)
```

### CTE vs Subquery

CTEs improve readability but may have different performance from subqueries.

```python
# CTE approach (more readable)
active_users = Q.select("id").from_("users").where("active", True).as_("active")
query = Q.select("*").with_(active_users).from_("orders").where_in("user_id", Q.select("id").from_("active"))

# Subquery approach (may be optimized differently by DB)
subquery = Q.select("id").from_("users").where("active", True)
query = Q.select("*").from_("orders").where_in("user_id", subquery)
```

## Best Practices

### Named and Organized

```python
# ✅ Good: Clear names, logical organization
user_stats = Q.select(...).as_("user_stats")
product_stats = Q.select(...).as_("product_stats")

query = (
    Q.select("*")
    .with_(user_stats)
    .with_(product_stats)
    .from_("user_stats us")
    .join("product_stats ps", "ps.user_id = us.user_id")
)

# ❌ Bad: Generic names, unclear purpose
cte1 = Q.select(...).as_("temp1")
cte2 = Q.select(...).as_("temp2")
```

### Limit CTE Complexity

```python
# ❌ Avoid: Too many nested CTEs
# (Hard to understand and debug)

# ✅ Better: Break into logical steps
step1 = Q.select(...).as_("filtered_data")
step2 = Q.select(...).with_(step1).from_("filtered_data").as_("aggregated")
final = Q.select(...).with_(step2).from_("aggregated")
```

### Document Complex CTEs

```python
# Complex recursive CTE - add comments
def get_category_tree(root_id):
    """Get all categories in a hierarchy starting from root_id."""
    
    # Base case: root category
    # Recursive case: all child categories
    cte = (
        Q.select("id", "name", "parent_id", Raw("1").as_("depth"))
        .from_("categories")
        .where("id", root_id)
        .union_all(
            Q.select("c.id", "c.name", "c.parent_id", Raw("tree.depth + 1"))
            .from_("categories c")
            .join("category_tree tree", "c.parent_id = tree.id")
        )
        .as_("category_tree")
    )
    
    return Q.select("*").with_(cte).from_("category_tree")
```

## Debugging CTEs

Use debug mode to inspect generated SQL:

```python
cte = Q.select("user_id", func.count("*")).from_("orders").group_by("user_id").as_("counts")

query = (
    Q.select("*")
    .with_(cte)
    .from_("counts")
    .debug()  # Enable debug output
)

sql, params = query.build()
# Prints the full SQL with CTE
```

## See Also

- [SELECT Queries](select.md) - Using CTEs in SELECT
- [Window Functions](window-functions.md) - Combining CTEs with window functions
- [UPDATE Queries](update.md) - Using CTEs in UPDATE
- [DELETE Queries](delete.md) - Using CTEs in DELETE
