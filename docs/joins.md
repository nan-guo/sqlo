# JOIN Operations

Complete guide to JOIN operations with sqlo.

## Basic JOINs

### INNER JOIN

The default `join()` method creates an INNER JOIN.

```python
from sqlo import Q, func

query = (
    Q.select("users.name", "orders.total")
    .from_("users")
    .join("orders", "orders.user_id = users.id")
)
# SELECT `users`.`name`, `orders`.`total` 
# FROM `users` 
# INNER JOIN `orders` ON orders.user_id = users.id
```

### LEFT JOIN

Use `left_join()` to include all rows from the left table, even if there are no matches in the right table.

```python
query = (
    Q.select("users.name", "orders.total")
    .from_("users")
    .left_join("orders", "orders.user_id = users.id")
)
# SELECT `users`.`name`, `orders`.`total` 
# FROM `users` 
# LEFT JOIN `orders` ON orders.user_id = users.id
```

### RIGHT JOIN

Use `right_join()` to include all rows from the right table.

```python
query = (
    Q.select("users.name", "orders.total")
    .from_("users")
    .right_join("orders", "orders.user_id = users.id")
)
# SELECT `users`.`name`, `orders`.`total` 
# FROM `users` 
# RIGHT JOIN `orders` ON orders.user_id = users.id
```

### CROSS JOIN

Use `cross_join()` to create a Cartesian product of rows from both tables.

```python
query = (
    Q.select("sizes.name", "colors.name")
    .from_("sizes")
    .cross_join("colors")
)
# SELECT `sizes`.`name`, `colors`.`name` 
# FROM `sizes` 
# CROSS JOIN `colors`
```

## Advanced JOIN Features

### Table Aliases

It is highly recommended to use aliases for readability and to avoid ambiguity.

```python
query = (
    Q.select("u.name", "o.total")
    .from_("users", alias="u")
    .join("orders AS o", "o.user_id = u.id")
)
# SELECT `u`.`name`, `o`.`total` 
# FROM `users` AS `u` 
# INNER JOIN `orders` AS `o` ON o.user_id = u.id
```

### Multiple JOINs

You can chain multiple JOINs to connect several tables.

```python
query = (
    Q.select("u.name", "p.title", "c.name as category")
    .from_("users", alias="u")
    .join("posts AS p", "p.user_id = u.id")
    .left_join("categories AS c", "c.id = p.category_id")
)
# SELECT `u`.`name`, `p`.`title`, `c`.`name` as category
# FROM `users` AS `u`
# INNER JOIN `posts` AS `p` ON p.user_id = u.id
# LEFT JOIN `categories` AS `c` ON c.id = p.category_id
```

### Complex JOIN Conditions

The `on` argument accepts three kinds of value:

- **A string** such as `"s.user_id = u.id"`: one column compared with another, with
  several comparisons optionally joined by `AND`. Only column names and the operators
  `=`, `!=`, `<>`, `<=>`, `<`, `<=`, `>`, `>=` are accepted. `<=>` is MySQL-only: on PostgreSQL it
  raises `UnsupportedFeatureError`. A `CROSS JOIN` takes no `ON` condition.
- **A `Condition`**: use it for literal values, which are bound as parameters, and for `OR`.
- **A `Raw`**: use it for functions and any other SQL. It is written as-is, so only pass
  trusted text; it can carry parameters too.

Anything else, such as a string with a literal, a function or `OR`, raises `ValueError`
that points to `Raw` or `Condition`. Other types raise `TypeError`.

```python
from sqlo import Condition, Q, Raw

# Several column comparisons: a string is enough
query = (
    Q.select("*")
    .from_("users", "u")
    .join("subscriptions AS s", "s.user_id = u.id AND s.start_date <= u.end_date")
)
# INNER JOIN `subscriptions` AS s ON s.user_id = u.id AND s.start_date <= u.end_date

# A literal value: use a Condition, the value is bound as a parameter
on = Condition("s.user_id", Raw("u.id")) & Condition("s.status", "active")
query = Q.select("*").from_("users", "u").join("subscriptions AS s", on)
# INNER JOIN `subscriptions` AS s ON (`s`.`user_id` = u.id AND `s`.`status` = %s)
# params: ("active",)

# A function: use Raw
query = Q.select("*").from_("dates", "d").left_join("sales s", Raw("DATE(s.created_at) = d.date"))
# LEFT JOIN `sales` s ON DATE(s.created_at) = d.date
```

Parameters in the `ON` clause come before the parameters of `WHERE`, matching the order
in the SQL.

### Joining Subqueries

You can join a subquery by treating it as a derived table.

```python
# Create a subquery
latest_orders = (
    Q.select("user_id", func.max("created_at").as_("last_order_date"))
    .from_("orders")
    .group_by("user_id")
)

# Join the subquery
query = (
    Q.select("u.name", "lo.last_order_date")
    .from_("users", alias="u")
    .join(latest_orders.as_("lo"), "lo.user_id = u.id")
)
# SELECT `u`.`name`, `lo`.`last_order_date`
# FROM `users` AS `u`
# INNER JOIN (SELECT `user_id`, MAX(created_at) as last_order_date FROM `orders` GROUP BY `user_id`) AS `lo` 
# ON lo.user_id = u.id
```

## Self Joins

You can join a table to itself using aliases.

```python
# Find employees and their managers
query = (
    Q.select("e.name as employee", "m.name as manager")
    .from_("employees", alias="e")
    .left_join("employees AS m", "m.id = e.manager_id")
)
# SELECT `e`.`name` as employee, `m`.`name` as manager
# FROM `employees` AS `e`
# LEFT JOIN `employees` AS `m` ON m.id = e.manager_id
```

## Performance Tips

1. **Index Foreign Keys**: Ensure columns used in ON clauses are indexed.
2. **Filter Early**: Use WHERE clauses to reduce the number of rows before joining if possible (though the optimizer usually handles this).
3. **Select Specific Columns**: Avoid `SELECT *` when joining multiple tables to prevent fetching unnecessary data.
4. **Use EXPLAIN**: Use the `explain()` method to check if your JOINs are using indexes efficiently.

```python
query = Q.select("*").from_("users").join("orders", "orders.user_id = users.id")
print(query.explain())
```

## Common Patterns

### Filtering by Related Existence

Find users who have at least one order (INNER JOIN):

```python
query = (
    Q.select("DISTINCT u.*")
    .from_("users", alias="u")
    .join("orders AS o", "o.user_id = u.id")
)
```

Find users who have NO orders (LEFT JOIN + WHERE NULL):

```python
query = (
    Q.select("u.*")
    .from_("users", alias="u")
    .left_join("orders AS o", "o.user_id = u.id")
    .where_null("o.id")
)
```

### Aggregating Related Data

Get user details with their order count:

```python
query = (
    Q.select("u.id", "u.name", func.count("o.id").as_("order_count"))
    .from_("users", alias="u")
    .left_join("orders AS o", "o.user_id = u.id")
    .group_by("u.id", "u.name")
)
```

## See Also

- [SELECT Queries](select.md) - Basic SELECT usage
- [Subqueries](select.md#subqueries) - Using subqueries
- [UPDATE Queries](update.md#update-multiple-tables-mysql) - Multi-table updates
