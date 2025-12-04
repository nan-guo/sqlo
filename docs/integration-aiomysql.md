# Integration with aiomysql

Complete guide to using sqlo with aiomysql for async database operations.

## Introduction

[aiomysql](https://github.com/aio-libs/aiomysql) is an async MySQL client for Python built on top of PyMySQL.  sqlo generates standard parameterized SQL queries that work seamlessly with aiomysql.

## Installation

```bash
pip install sqlo aiomysql

# Or with uv
uv add sqlo aiomysql
```

## Basic Usage

### Creating a Connection Pool

```python
import aiomysql
import asyncio
from sqlo import Q

async def create_pool():
    """Create aiomysql connection pool."""
    pool = await aiomysql.create_pool(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        db='mydb',
        autocommit=False,
        minsize=1,
        maxsize=10
    )
    return pool

# Usage
async def main():
    pool = await create_pool()
    # Use pool...
    pool.close()
    await pool.wait_closed()
```

### Simple SELECT Query

```python
async def get_user(pool, user_id: int):
    """Fetch a user by ID."""
    query = Q.select("id", "name", "email").from_("users").where("id", user_id)
    sql, params = query.build()
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(sql, params)
            result = await cursor.fetchone()
            return result

# Usage
# user = await get_user(pool, 123)
# print(user)  # {'id': 123, 'name': 'Alice', ...}
```

### INSERT Query

```python
async def create_user(pool, name: str, email: str):
    """Create a new user."""
    query = Q.insert_into("users").values([{
        "name": name,
        "email": email,
        "created_at": "NOW()"
    }])
    sql, params = query.build()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            await conn.commit()
            return cursor.lastrowid

# Usage
# user_id = await create_user(pool, "Bob", "bob@example.com")
```

### UPDATE Query

```python
async def update_user(pool, user_id: int, **updates):
    """Update user fields."""
    query = (
        Q.update("users")
        .set(updates)
        .where("id", user_id)
    )
    sql, params = query.build()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

# Usage
# rows_updated = await update_user(pool, 123, name="Alice Updated")
```

### DELETE Query

```python
async def delete_user(pool, user_id: int):
    """Delete a user by ID."""
    query = Q.delete_from("users").where("id", user_id)
    sql, params = query.build()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            await conn.commit()
            return cursor.rowcount

# Usage
# deleted = await delete_user(pool, 123)
```

## Advanced Patterns

### Generic Query Executor

```python
from typing import List, Dict, Any, Optional

class AsyncDatabase:
    """Async database wrapper using sqlo and aiomysql."""
    
    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
    
    async def fetch_one(self, query) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        sql, params = query.build()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                return await cursor.fetchone()
    
    async def fetch_all(self, query) -> List[Dict[str, Any]]:
        """Fetch all matching rows."""
        sql, params = query.build()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                return await cursor.fetchall()
    
    async def execute(self, query) -> int:
        """Execute a query and return affected row count."""
        sql, params = query.build()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                await conn.commit()
                return cursor.rowcount
    
    async def insert(self, query) -> int:
        """Execute INSERT and return last inserted ID."""
        sql, params = query.build()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                await conn.commit()
                return cursor.lastrowid

# Usage
async def main():
    pool = await create_pool()
    db = AsyncDatabase(pool)
    
    # Fetch one
    user = await db.fetch_one(
        Q.select("*").from_("users").where("id", 123)
    )
    
    # Fetch all
    users = await db.fetch_all(
        Q.select("*").from_("users").where("active", True)
    )
    
    # Insert
    user_id = await db.insert(
        Q.insert_into("users").values([{"name": "Alice", "email": "alice@example.com"}])
    )
    
    # Update
    updated = await db.execute(
        Q.update("users").set({"active": False}).where("id", user_id)
    )
    
    pool.close()
    await pool.wait_closed()
```

### Transaction Management

```python
async def transfer_funds(pool, from_account: int, to_account: int, amount: float):
    """Transfer funds between accounts within a transaction."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                # Start transaction (autocommit is False in pool config)
                await conn.begin()
                
                # Deduct from source account
                deduct_query = (
                    Q.update("accounts")
                    .set({"balance": "balance - %s"})
                    .where("id", from_account)
                )
                sql, params = deduct_query.build()
                await cursor.execute(sql, (amount,) + params[1:])
                
                # Add to destination account
                add_query = (
                    Q.update("accounts")
                    .set({"balance": "balance + %s"})
                    .where("id", to_account)
                )
                sql, params = add_query.build()
                await cursor.execute(sql, (amount,) + params[1:])
                
                # Commit transaction
                await conn.commit()
                return True
                
            except Exception as e:
                # Rollback on error
                await conn.rollback()
                raise Exception(f"Transfer failed: {e}")
```

### Batch Operations

```python
async def batch_insert_users(pool, users: List[Dict[str, Any]], chunk_size: int = 500):
    """Insert users in batches."""
    total_inserted = 0
    
    for i in range(0, len(users), chunk_size):
        chunk = users[i:i + chunk_size]
        query = Q.insert_into("users").values(chunk)
        sql, params = query.build()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                await conn.commit()
                total_inserted += cursor.rowcount
    
    return total_inserted

# Usage
# users = [{"name": f"User{i}", "email": f"user{i}@example.com"} for i in range(1000)]
# inserted = await batch_insert_users(pool, users)
```

### Pagination Helper

```python
from typing import Tuple

async def paginate(
    pool,
    base_query,
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Paginate query results.
    
    Returns: (results, total_count)
    """
    # Get total count
    count_query = Q.select("COUNT(*) as total").from_(
        base_query.as_("subquery")
    )
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # Get count
            sql, params = count_query.build()
            await cursor.execute(sql, params)
            count_result = await cursor.fetchone()
            total = count_result['total']
            
            # Get paginated results
            paginated_query = base_query.paginate(page=page, per_page=per_page)
            sql, params = paginated_query.build()
            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            
            return results, total

# Usage
async def get_users_page(pool, page: int = 1):
    base_query = Q.select("*").from_("users").where("active", True).order_by("-created_at")
    results, total = await paginate(pool, base_query, page=page, per_page=20)
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "pages": (total + 19) // 20  # Ceiling division
    }
```

## Context Manager Pattern

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_connection(pool):
    """Context manager for database connections."""
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)

@asynccontextmanager
async def db_transaction(pool):
    """Context manager for transactions."""
    async with db_connection(pool) as conn:
        try:
            await conn.begin()
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

# Usage
async def create_user_with_profile(pool, user_data: dict, profile_data: dict):
    """Create user and profile in a transaction."""
    async with db_transaction(pool) as conn:
        async with conn.cursor() as cursor:
            # Insert user
            user_query = Q.insert_into("users").values([user_data])
            sql, params = user_query.build()
            await cursor.execute(sql, params)
            user_id = cursor.lastrowid
            
            # Insert profile
            profile_data['user_id'] = user_id
            profile_query = Q.insert_into("profiles").values([profile_data])
            sql, params = profile_query.build()
            await cursor.execute(sql, params)
            
            return user_id
```

## Error Handling

```python
import aiomysql.err as mysql_errors

async def safe_insert_user(pool, email: str, name: str):
    """Insert user with duplicate key handling."""
    query = Q.insert_into("users").values([{
        "email": email,
        "name": name
    }])
    sql, params = query.build()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(sql, params)
                await conn.commit()
                return {"success": True, "id": cursor.lastrowid}
            except mysql_errors.IntegrityError as e:
                if e.args[0] == 1062:  # Duplicate entry
                    return {"success": False, "error": "Email already exists"}
                raise
            except Exception as e:
                await conn.rollback()
                return {"success": False, "error": str(e)}
```

## Connection Pool Best Practices

```python
# Configure pool appropriately
pool = await aiomysql.create_pool(
    host='localhost',
    port=3306,
    user='user',
    password='password',
    db='database',
    autocommit=False,  # Explicit transaction control
    minsize=5,         # Minimum connections
    maxsize=20,        # Maximum connections
    pool_recycle=3600, # Recycle connections every hour
    echo=False,        # Set True for SQL logging
)

# Use context managers
async with pool.acquire() as conn:
    async with conn.cursor() as cursor:
        # Query execution
        pass

# Clean up on shutdown
pool.close()
await pool.wait_closed()
```

## FastAPI Integration Example

```python
from fastapi import FastAPI, Depends
from typing import Optional
import aiomysql

app = FastAPI()

# Global pool
db_pool: Optional[aiomysql.Pool] = None

@app.on_event("startup")
async def startup():
    """Create database pool on startup."""
    global db_pool
    db_pool = await aiomysql.create_pool(
        host='localhost',
        port=3306,
        user='user',
        password='password',
        db='mydb',
        minsize=5,
        maxsize=20
    )

@app.on_event("shutdown")
async def shutdown():
    """Close pool on shutdown."""
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()

async def get_db():
    """Dependency for database access."""
    return AsyncDatabase(db_pool)

@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncDatabase = Depends(get_db)):
    """Get user by ID."""
    query = Q.select("*").from_("users").where("id", user_id)
    user = await db.fetch_one(query)
    
    if user:
        return user
    return {"error": "User not found"}, 404

@app.post("/users")
async def create_user(name: str, email: str, db: AsyncDatabase = Depends(get_db)):
    """Create a new user."""
    query = Q.insert_into("users").values([{
        "name": name,
        "email": email
    }])
    user_id = await db.insert(query)
    return {"id": user_id, "name": name, "email": email}

@app.get("/users")
async def list_users(page: int = 1, db: AsyncDatabase = Depends(get_db)):
    """List users with pagination."""
    base_query = Q.select("*").from_("users").order_by("-created_at")
    results, total = await paginate(db_pool, base_query, page=page, per_page=20)
    
    return {
        "results": results,
        "total": total,
        "page": page
    }
```

## Performance Tips

1. **Use Connection Pooling**: Always use a connection pool, never create connections per request
2. **Batch Operations**: Use batch inserts/updates for multiple records
3. **Prepared Statements**: sqlo generates parameterized queries automatically
4. **Transaction Management**: Group related operations in transactions
5. **Index Usage**: Ensure database tables have appropriate indexes

## See Also

- [Batch Operations](batch-operations.md) - Efficient bulk operations
- [SELECT Queries](select.md) - Query building
- [Security Guide](security.md) - SQL injection prevention
- [aiomysql Documentation](https://aiomysql.readthedocs.io/)
