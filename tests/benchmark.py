"""
Benchmark suite for SQL Toolkit performance testing.

Run with: python -m tests.benchmark
"""

import time
from functools import wraps

from sqlo import Condition, Q, func


def benchmark(name: str, iterations: int = 10000):
    """Decorator to benchmark a function."""

    def decorator(func):
        @wraps(func)
        def wrapper():
            start = time.perf_counter()
            for _ in range(iterations):
                func()
            end = time.perf_counter()
            elapsed = (end - start) * 1000  # Convert to ms
            avg = elapsed / iterations
            print(f"{name:50} | {elapsed:>10.2f}ms total | {avg:>8.4f}ms avg")
            return elapsed

        return wrapper

    return decorator


# Benchmark 1: Simple SELECT
@benchmark("Simple SELECT with 1 WHERE", 10000)
def bench_simple_select():
    Q.select("id", "name").from_("users").where("active", True).build()


# Benchmark 2: Complex SELECT
@benchmark("Complex SELECT (10 WHERE + 5 JOIN)", 5000)
def bench_complex_select():
    q = Q.select("u.id", "u.name", func.count("o.id"))
    q.from_("users", alias="u")
    q.left_join("orders o1", on="u.id = o1.user_id")
    q.left_join("orders o2", on="u.id = o2.user_id")
    q.left_join("orders o3", on="u.id = o3.user_id")
    q.left_join("orders o4", on="u.id = o4.user_id")
    q.left_join("orders o5", on="u.id = o5.user_id")
    for i in range(10):
        q.where(f"col{i} >", i)
    q.group_by("u.id")
    q.order_by("-count")
    q.build()


# Benchmark 3: WHERE IN with large list
@benchmark("WHERE IN with 100 values", 10000)
def bench_where_in():
    ids = list(range(100))
    Q.select("*").from_("users").where_in("id", ids).build()


# Benchmark 4: WHERE IN with small list (cache hit)
@benchmark("WHERE IN with 10 values (cached)", 10000)
def bench_where_in_cached():
    ids = list(range(10))
    # Run twice to ensure cache is warmed up
    Q.select("*").from_("users").where_in("id", ids).build()
    Q.select("*").from_("users").where_in("id", ids).build()


# Benchmark 5: Batch INSERT
@benchmark("Batch INSERT (100 rows)", 1000)
def bench_batch_insert():
    rows = [
        {"name": f"User{i}", "age": i, "email": f"user{i}@example.com"}
        for i in range(100)
    ]
    Q.insert_into("users").values(rows).build()


# Benchmark 6: Complex Conditions
@benchmark("Complex Condition (nested AND/OR)", 5000)
def bench_complex_conditions():
    cond = (Condition("age >", 18) & Condition("country", "FR")) | (
        Condition("vip", True) & Condition("status", "active")
    )
    Q.select("*").from_("users").where(cond).build()


# Benchmark 7: UNION of 5 queries
@benchmark("UNION of 5 queries", 2000)
def bench_union():
    q1 = Q.select("id").from_("users").where("type", 1)
    q2 = Q.select("id").from_("users").where("type", 2)
    q3 = Q.select("id").from_("users").where("type", 3)
    q4 = Q.select("id").from_("users").where("type", 4)
    q5 = Q.select("id").from_("users").where("type", 5)
    q1.union(q2).union(q3).union(q4).union(q5).build()


# Benchmark 8: GROUP BY with 20 columns
@benchmark("GROUP BY with 20 columns", 5000)
def bench_group_by():
    cols = [f"col{i}" for i in range(20)]
    Q.select(*cols).from_("users").group_by(*cols).build()


# Benchmark 9: Repeated quote() calls (cache effectiveness)
@benchmark("Repeated quote() on same columns", 10000)
def bench_quote_cache():
    # This should benefit from LRU cache
    for _ in range(10):
        Q.select("id", "name", "email", "created_at").from_("users").build()


# Benchmark 10: UPDATE with complex WHERE
@benchmark("UPDATE with 5 WHERE clauses", 5000)
def bench_update():
    Q.update("users").set({"active": True, "updated_at": "2023-01-01"}).where(
        "id >", 100
    ).where("status", "pending").build()


if __name__ == "__main__":
    print("=" * 80)
    print("SQL Toolkit Performance Benchmark")
    print("=" * 80)
    print(f"{'Test Name':<50} | {'Total Time':>10} | {'Avg Time':>8}")
    print("-" * 80)

    bench_simple_select()
    bench_complex_select()
    bench_where_in()
    bench_where_in_cached()
    bench_batch_insert()
    bench_complex_conditions()
    bench_union()
    bench_group_by()
    bench_quote_cache()
    bench_update()

    print("=" * 80)
