# Expressions & Functions

Guide to using SQL functions and raw expressions in sqlo.

## Raw SQL Expressions

Sometimes you need to inject raw SQL fragments that the query builder doesn't support natively. The `Raw` class allows this safely.

```python
from sqlo import Q, Raw

# Use raw SQL in SELECT
query = Q.select("id", Raw("NOW() as current_time")).from_("users")
# SELECT `id`, NOW() as current_time FROM `users`

# Use raw SQL in WHERE
query = Q.select("*").from_("users").where(Raw("LENGTH(name) > 10"))
# WHERE LENGTH(name) > 10
```

### Parameter Binding with Raw

You can safely bind parameters to raw expressions to prevent SQL injection.

```python
# Safe raw expression with parameters
query = Q.select("*").from_("users").where(
    Raw("DATEDIFF(NOW(), created_at) > %s", [30])
)
# WHERE DATEDIFF(NOW(), created_at) > %s
# Params: (30,)
```

## SQL Functions

The toolkit provides a `Func` factory for generating standard SQL function calls.

```python
from sqlo import Func

# COUNT
query = Q.select(Func.count("*")).from_("users")
# SELECT COUNT(*) FROM `users`

# MAX, MIN, AVG, SUM
query = Q.select(
    Func.max("price"),
    Func.min("price"),
    Func.avg("rating")
).from_("products")
# SELECT MAX(`price`), MIN(`price`), AVG(`rating`) FROM `products`
```

### Custom Functions

You can create any function call using `Func.custom()`.

```python
# Custom function
query = Q.select(Func.custom("GROUP_CONCAT", "name")).from_("users")
# SELECT GROUP_CONCAT(`name`) FROM `users`

# Function with multiple arguments
query = Q.select(Func.custom("CONCAT", "first_name", "' '", "last_name")).from_("users")
# SELECT CONCAT(`first_name`, ' ', `last_name`) FROM `users`
```

## Safety Notes

### SQL Injection Prevention

The query builder automatically handles parameter binding for standard methods (`where`, `insert`, `update`). However, when using `Raw`, you must be careful.

**❌ Unsafe (Vulnerable to Injection):**
```python
user_input = "'; DROP TABLE users; --"
# NEVER DO THIS:
query = Q.select("*").from_("users").where(Raw(f"name = '{user_input}'"))
```

**✅ Safe (Parameterized):**
```python
user_input = "Alice"
# DO THIS:
query = Q.select("*").from_("users").where(Raw("name = %s", [user_input]))
```

### Identifier Quoting

The builder automatically quotes identifiers (table and column names) with backticks (`` ` ``) to prevent conflicts with reserved keywords.

```python
# Automatically quoted
query = Q.select("order", "group").from_("select")
# SELECT `order`, `group` FROM `select`
```

If you use `Raw`, you are responsible for quoting identifiers if necessary.

```python
# You must quote manually in Raw
query = Q.select(Raw("`order` + 1")).from_("items")
```

## See Also

- [SELECT Queries](select.md) - Using expressions in SELECT
- [UPDATE Queries](update.md) - Using expressions in SET clauses
- [Condition Objects](conditions.md) - Using expressions in conditions
