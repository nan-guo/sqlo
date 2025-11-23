# Condition Objects

Guide to using `Condition` and `ComplexCondition` objects for advanced query filtering.

## Overview

While simple `where()` calls are sufficient for most queries, `Condition` objects provide a powerful way to build complex, nested logical expressions with mixed AND/OR logic.

## The Condition Class

The `Condition` class represents a single SQL condition.

```python
from sqlo import Condition

# Create a condition
c = Condition("age", ">=", 18)
# Represents: `age` >= ?
```

### Supported Operators

- Standard: `=`, `!=`, `>`, `<`, `>=`, `<=`
- SQL specific: `LIKE`, `NOT LIKE`, `IN`, `NOT IN`, `IS`, `IS NOT`
- Custom: Any string operator

```python
Condition("name", "LIKE", "A%")
Condition("status", "IN", ["active", "pending"])
Condition("deleted_at", "IS", None)
```

## Complex Combinations

You can combine conditions using `and_()` and `or_()` static methods or bitwise operators.

### Using Static Methods (Recommended)

```python
# (age >= 18 AND country = 'US')
c = Condition.and_(
    Condition("age", ">=", 18),
    Condition("country", "=", "US")
)

# (status = 'active' OR status = 'pending')
c = Condition.or_(
    Condition("status", "=", "active"),
    Condition("status", "=", "pending")
)
```

### Nesting Conditions

You can nest `and_` and `or_` to create arbitrarily complex logic.

```python
# (active = 1 AND (role = 'admin' OR (role = 'user' AND points > 100)))
c = Condition.and_(
    Condition("active", "=", True),
    Condition.or_(
        Condition("role", "=", "admin"),
        Condition.and_(
            Condition("role", "=", "user"),
            Condition("points", ">", 100)
        )
    )
)
```

### Using Bitwise Operators

You can also use `&` (AND) and `|` (OR) operators, but be careful with operator precedence (always use parentheses).

```python
c1 = Condition("age", ">=", 18)
c2 = Condition("country", "=", "US")

# AND combination
combined = c1 & c2

# OR combination
combined = c1 | c2

# Complex combination
combined = c1 & (c2 | Condition("country", "=", "CA"))
```

## Using Conditions in Queries

Pass the condition object directly to `where()` or `having()`.

```python
from sqlo import Q, Condition

# Define complex logic
is_eligible = Condition.or_(
    Condition("age", ">=", 21),
    Condition.and_(
        Condition("age", ">=", 18),
        Condition("has_consent", "=", True)
    )
)

# Use in query
query = Q.select("*").from_("users").where(is_eligible)
# WHERE (`age` >= ? OR (`age` >= ? AND `has_consent` = ?))
```

## Dynamic Condition Building

Condition objects are excellent for building filters dynamically.

```python
def build_filter(filters: dict):
    conditions = []
    
    if "status" in filters:
        conditions.append(Condition("status", "=", filters["status"]))
        
    if "min_price" in filters:
        conditions.append(Condition("price", ">=", filters["min_price"]))
        
    if "search" in filters:
        term = f"%{filters['search']}%"
        conditions.append(Condition.or_(
            Condition("title", "LIKE", term),
            Condition("description", "LIKE", term)
        ))
    
    if not conditions:
        return None
        
    # Combine all with AND
    return Condition.and_(*conditions)

# Usage
filters = {"status": "active", "search": "python"}
where_clause = build_filter(filters)

if where_clause:
    query = Q.select("*").from_("products").where(where_clause)
```

## Raw SQL Conditions

For conditions that can't be expressed with standard operators, use `Raw`.

```python
from sqlo import Raw

# Raw SQL condition
c = Condition(Raw("LENGTH(password)"), ">", 8)
# LENGTH(password) > ?

# Completely raw condition
c = Condition(Raw("MATCH(title, body) AGAINST(?)", ["search term"]))
```

## See Also

- [SELECT Queries](select.md#where-clauses) - Basic WHERE usage
- [Expressions & Functions](expressions.md) - Using raw SQL and functions
