# Recipes and Best Practices

Collection of common patterns and best practices for using sqlo effectively.

## CRUD Operations

### User Management

```python
from sqlo import Q
from typing import Optional, List, Dict, Any

class UserRepository:
    """Repository pattern for user operations."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create(self, name: str, email: str) -> int:
        """Create a new user."""
        query = Q.insert_into("users").values([{
            "name": name,
            "email": email,
            "created_at": "NOW()"
        }])
        cursor = self.db.cursor()
        cursor.execute(*query.build())
        self.db.commit()
        return cursor.lastrowid
    
    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = Q.select("*").from_("users").where("id", user_id)
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(*query.build())
        return cursor.fetchone()
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        query = Q.select("*").from_("users").where("email", email)
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(*query.build())
        return cursor.fetchone()
    
    def list_active(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List active users."""
        query = (
            Q.select("*")
            .from_("users")
            .where("active", True)
            .order_by("-created_at")
            .limit(limit)
        )
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(*query.build())
        return cursor.fetchall()
    
    def update(self, user_id: int, **fields) -> bool:
        """Update user fields."""
        fields["updated_at"] = "NOW()"
        query = Q.update("users").set(fields).where("id", user_id)
        cursor = self.db.cursor()
        cursor.execute(*query.build())
        self.db.commit()
        return cursor.rowcount > 0
    
    def delete(self, user_id: int) -> bool:
        """Delete a user."""
        query = Q.delete_from("users").where("id", user_id)
        cursor = self.db.cursor()
        cursor.execute(*query.build())
        self.db.commit()
        return cursor.rowcount > 0
    
    def soft_delete(self, user_id: int) -> bool:
        """Soft delete (mark as deleted)."""
        return self.update(user_id, deleted_at="NOW()", active=False)
```

## Search and Filtering

### Dynamic Search Builder

```python
from typing import Optional

def build_search_query(
    search: Optional[str] = None,
    status: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    tags: Optional[List[str]] = None,
    page: int = 1,
    per_page: int = 20
):
    """Build a search query with optional filters."""
    query = Q.select("*").from_("users")
    
    # Text search
    if search:
        query = query.where_like("name", f"%{search}%")
    
    # Status filter
    if status:
        query = query.where("status", status)
    
    # Age range
    if min_age is not None:
        query = query.where("age >=", min_age)
    if max_age is not None:
        query = query.where("age <=", max_age)
    
    # Tags (using JSON or separate table)
    if tags:
        query = query.where_in("tag_id", tags)
    
    # Pagination
    query = query.order_by("-created_at").paginate(page=page, per_page=per_page)
    
    return query

# Usage
query = build_search_query(
    search="John",
    status="active",
    min_age=18,
    tags=[1, 2, 3],
    page=1
)
```

### Full-Text Search

```python
from sqlo import Raw

def fulltext_search(keywords: str, limit: int = 10):
    """Full-text search using MySQL."""
    query = (
        Q.select(
            "*",
            Raw(f"MATCH(title, content) AGAINST(%s)", [keywords]).as_("relevance")
        )
        .from_("articles")
        .where(Raw(f"MATCH(title, content) AGAINST(%s)", [keywords]))
        .order_by(Raw("relevance DESC"))
        .limit(limit)
    )
    return query
```

## Aggregations and Reports

### Sales Report

```python
from sqlo import func, Window

def monthly_sales_report(year: int):
    """Generate monthly sales report."""
    query = (
        Q.select(
            Raw(f"DATE_FORMAT(created_at, '%Y-%m')").as_("month"),
            func.count("*").as_("order_count"),
            func.sum("total").as_("total_sales"),
            func.avg("total").as_("avg_order_value"),
            func.min("total").as_("min_order"),
            func.max("total").as_("max_order")
        )
        .from_("orders")
        .where("YEAR(created_at)", year)
        .group_by(Raw("DATE_FORMAT(created_at, '%Y-%m')"))
        .order_by("month")
    )
    return query
```

### Top N per Category

```python
def top_products_by_category(n: int = 5):
    """Get top N products in each category."""
    ranked = (
        Q.select(
            "category_id",
            "product_id",
            "name",
            "sales",
            func.row_number().over(
                Window.partition_by("category_id").and_order_by("-sales")
            ).as_("rank")
        )
        .from_("products")
        .as_("ranked")
    )
    
    query = (
        Q.select("*")
        .with_(ranked)
        .from_("ranked")
        .where("rank <=", n)
    )
    return query
```

## Data Transformation

### Pivot Table

```python
def sales_pivot_by_month_and_product():
    """Pivot sales data by month and product."""
    query = Q.select(
        Raw("DATE_FORMAT(created_at, '%Y-%m')").as_("month"),
        Raw("SUM(CASE WHEN product_id = 1 THEN total ELSE 0 END)").as_("product_1"),
        Raw("SUM(CASE WHEN product_id = 2 THEN total ELSE 0 END)").as_("product_2"),
        Raw("SUM(CASE WHEN product_id = 3 THEN total ELSE 0 END)").as_("product_3"),
        func.sum("total").as_("total")
    ).from_("sales").group_by(Raw("DATE_FORMAT(created_at, '%Y-%m')"))
    
    return query
```

### Data Normalization

```python
def normalize_user_data():
    """Extract first_name and last_name from full_name."""
    query = (
        Q.update("users")
        .set({
            "first_name": Raw("SUBSTRING_INDEX(full_name, ' ', 1)"),
            "last_name": Raw("SUBSTRING_INDEX(full_name, ' ', -1)")
        })
        .where_null("first_name")
    )
    return query
```

## Complex Joins

### Multi-Level Join

```python
def get_orders_with_details():
    """Get orders with user, product, and category info."""
    query = (
        Q.select(
            "o.id as order_id",
            "u.name as customer_name",
            "u.email",
            "p.name as product_name",
            "c.name as category_name",
            "o.quantity",
            "o.total"
        )
        .from_("orders o")
        .join("users u", "u.id = o.user_id")
        .join("products p", "p.id = o.product_id")
        .join("categories c", "c.id = p.category_id")
        .where("o.created_at >", "2024-01-01")
        .order_by("-o.created_at")
    )
    return query
```

### Self Join

```python
def get_employee_hierarchy():
    """Get employees with their managers."""
    query = (
        Q.select(
            "e.id",
            "e.name as employee_name",
            "e.title",
            "m.name as manager_name",
            "m.title as manager_title"
        )
        .from_("employees e")
        .left_join("employees m", "m.id = e.manager_id")
        .order_by("m.name", "e.name")
    )
    return query
```

## Performance Optimization

### Query Result Caching

```python
import hashlib
import json
from functools import lru_cache

class QueryCache:
    """Simple query result cache."""
    
    def __init__(self):
        self._cache = {}
    
    def _get_cache_key(self, sql: str, params: tuple) -> str:
        """Generate cache key from SQL and params."""
        cache_str = f"{sql}:{json.dumps(params)}"
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, query):
        """Get cached result if exists."""
        sql, params = query.build()
        key = self._get_cache_key(sql, params)
        return self._cache.get(key)
    
    def set(self, query, result, ttl: int = 300):
        """Cache query result."""
        sql, params = query.build()
        key = self._get_cache_key(sql, params)
        self._cache[key] = result
        # In production, use Redis with TTL
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries."""
        if pattern is None:
            self._cache.clear()
        else:
            # Implement pattern matching
            pass

# Usage
cache = QueryCache()

def get_popular_products(cache: QueryCache):
    query = Q.select("*").from_("products").where("featured", True).limit(10)
    
    # Check cache
    cached = cache.get(query)
    if cached:
        return cached
    
    # Execute query
    cursor = db.cursor(dictionary=True)
    cursor.execute(*query.build())
    results = cursor.fetchall()
    
    # Cache results
    cache.set(query, results, ttl=600)
    return results
```

### Efficient Pagination

```python
def cursor_based_pagination(last_id: Optional[int] = None, limit: int = 20):
    """Cursor-based pagination (more efficient than OFFSET)."""
    query = Q.select("*").from_("posts").order_by("id").limit(limit)
    
    if last_id:
        query = query.where("id >", last_id)
    
    return query

# Usage
# First page
results = cursor_based_pagination(limit=20)

# Next page (using last ID from previous results)
last_id = results[-1]['id']
next_results = cursor_based_pagination(last_id=last_id, limit=20)
```

## Data Integrity

### Unique Constraint Handling

```python
def upsert_user(email: str, name: str):
    """Insert or update user if email exists."""
    query = (
        Q.insert_into("users")
        .values([{"email": email, "name": name}])
        .on_duplicate_key_update({"name": name, "updated_at": "NOW()"})
    )
    return query
```

### Referential Integrity Check

```python
def delete_user_cascade(user_id: int):
    """Delete user and all related records."""
    # Note: This is manual cascade, better to use foreign keys with ON DELETE CASCADE
    
    # Delete related records first
    queries = [
        Q.delete_from("user_sessions").where("user_id", user_id),
        Q.delete_from("user_preferences").where("user_id", user_id),
        Q.delete_from("orders").where("user_id", user_id),
        Q.delete_from("users").where("id", user_id)
    ]
    
    cursor = db.cursor()
    try:
        db.begin()
        for query in queries:
            cursor.execute(*query.build())
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
```

## Audit Logging

### Automatic Audit Trail

```python
def create_audit_trigger(table: str, action: str, user_id: int, record_id: int):
    """Create audit log entry."""
    query = Q.insert_into("audit_log").values([{
        "table_name": table,
        "action": action,
        "user_id": user_id,
        "record_id": record_id,
        "timestamp": "NOW()"
    }])
    return query

def update_with_audit(table: str, record_id: int, user_id: int, **fields):
    """Update record with audit logging."""
    # Update main record
    update_query = Q.update(table).set(fields).where("id", record_id)
    
    # Create audit log
    audit_query = create_audit_trigger(table, "UPDATE", user_id, record_id)
    
    cursor = db.cursor()
    try:
        db.begin()
        cursor.execute(*update_query.build())
        cursor.execute(*audit_query.build())
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
```

## Testing Helpers

### Query Assertion Helpers

```python
def assert_query_equals(query, expected_sql: str, expected_params: tuple):
    """Assert that query generates expected SQL."""
    sql, params = query.build()
    assert sql == expected_sql, f"SQL mismatch:\nGot: {sql}\nExpected: {expected_sql}"
    assert params == expected_params, f"Params mismatch:\nGot: {params}\nExpected: {expected_params}"

# Usage in tests
def test_user_query():
    query = Q.select("*").from_("users").where("id", 123)
    assert_query_equals(
        query,
        "SELECT * FROM `users` WHERE `id` = %s",
        (123,)
    )
```

### Mock Database for Testing

```python
class MockCursor:
    """Mock database cursor for testing."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.executed_sql = []
        self.executed_params = []
        self.rowcount = 1
        self.lastrowid = 1
    
    def execute(self, sql, params):
        self.executed_sql.append(sql)
        self.executed_params.append(params)
    
    def fetchone(self):
        return self.return_value
    
    def fetchall(self):
        return [self.return_value] if self.return_value else []

# Usage in tests
def test_user_repository():
    mock_cursor = MockCursor(return_value={"id": 1, "name": "Alice"})
    
    # Test query building
    query = Q.select("*").from_("users").where("id", 1)
    mock_cursor.execute(*query.build())
    
    assert "SELECT" in mock_cursor.executed_sql[0]
    assert mock_cursor.executed_params[0] == (1,)
```

## See Also

- [SELECT Queries](select.md) - Query building
- [Window Functions](window-functions.md) - Advanced analytics
- [CTE](cte.md) - Common table expressions
- [Batch Operations](batch-operations.md) - Bulk operations
- [Integration with aiomysql](integration-aiomysql.md) - Async operations
