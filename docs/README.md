# Documentation Index

sqlo documentation navigation.

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Getting Started](getting-started.md)** - Installation, basic usage, core concepts
- **[Dialects](dialects.md)** - MySQL and PostgreSQL: choosing a dialect, what each supports, writing portable code

### 📖 Query Types
- **[SELECT Queries](select.md)** - Complete SELECT functionality (WHERE, ORDER BY, LIMIT, DISTINCT, UNION, etc.)
- **[INSERT Queries](insert.md)** - Single/batch inserts, INSERT IGNORE, ON DUPLICATE KEY UPDATE, portable `on_conflict()`  
- **[UPDATE Queries](update.md)** - UPDATE, SET, WHERE, LIMIT, ORDER BY
- **[DELETE Queries](delete.md)** - DELETE, WHERE, LIMIT, ORDER BY, safety best practices

### 🔧 SQL Features
- **[JOIN Operations](joins.md)** - INNER, LEFT, RIGHT, CROSS JOIN and performance optimization
- **[Condition Objects](conditions.md)** - Condition, ComplexCondition, AND/OR combinations
- **[Expressions & Functions](expressions.md)** - Raw SQL, Func, FunctionFactory, common functions

## 🎯 Find by Use Case

### I want to...

- **Query data** → [SELECT Queries](select.md)
- **Insert data** → [INSERT Queries](insert.md)
- **Update data** → [UPDATE Queries](update.md)
- **Delete data** → [DELETE Queries](delete.md)
- **Join multiple tables** → [JOIN Operations](joins.md)
- **Build complex conditions** → [Condition Objects](conditions.md)
- **Use SQL functions** → [Expressions & Functions](expressions.md)
- **Write raw SQL** → [Raw SQL Expressions](expressions.md#raw-sql-expressions)
- **Use PostgreSQL, or both databases** → [Dialects](dialects.md)

## 🔗 Quick Links

### Common Features
- [Basic SELECT](select.md#basic-queries)
- [WHERE conditions](select.md#where-clauses)
- [JOIN tables](joins.md)
- [Batch inserts](insert.md#batch-insert)
- [Pagination](select.md#limit-and-offset)

### Advanced Features
- [Complex conditions](conditions.md#complex-combinations)
- [Subqueries](select.md#subqueries)
- [UNION](select.md#union)
- [Index Hints](select.md#index-hints)

### Security
- [Parameterized queries](getting-started.md#parameterized-queries)
- [SQL injection protection](expressions.md#safety-notes)
- [DELETE safety](delete.md#safety-best-practices)

## 🆘 Need Help?

1. **Check examples** - Each document contains rich code examples
2. **Search docs** - Use Ctrl+F to search for keywords
3. **Check tests** - `tests/unit/` directory contains more use cases
4. **Open an issue** - If you find problems or have suggestions

---

**Get started** → [Getting Started](getting-started.md)
