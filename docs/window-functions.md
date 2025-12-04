# Window Functions

Complete guide to using SQL window functions with sqlo.

## Introduction

Window functions perform calculations across a set of rows that are related to the current row. Unlike aggregate functions that collapse rows, window functions preserve the original rows while adding computed information.

## Basic Concepts

A window function consists of:
- **Function**: The calculation to perform (ROW_NUMBER, SUM, AVG, etc.)
- **OVER clause**: Defines the window of rows
- **PARTITION BY**: Divides rows into partitions (optional)
- **ORDER BY**: Defines the order within partitions (optional)
- **Frame clause**: Specifies the exact subset of rows (optional)

## Creating Windows

The `Window` class provides a fluent API for defining window specifications.

```python
from sqlo import Q, Window, func

# Partition by department, order by salary
window = Window.partition_by("department").and_order_by("-salary")

# Order by date only
window = Window.order_by("date")

# Multiple partitions and ordering
window = (
    Window.partition_by("department", "region")
    .and_order_by("hire_date", "-salary")
)
```

## Ranking Functions

### ROW_NUMBER()

Assigns a unique sequential number to each row within a partition.

```python
# Rank employees within each department by salary
query = Q.select(
    "name",
    "department",
    "salary",
    func.row_number().over(
        Window.partition_by("department").and_order_by("-salary")
    ).as_("rank")
).from_("employees")

# SQL: SELECT `name`, `department`, `salary`,
#   ROW_NUMBER() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
# FROM `employees`
```

### RANK()

Similar to ROW_NUMBER, but gives the same rank to rows with equal values, leaving gaps.

```python
query = Q.select(
    "name",
    "score",
    func.rank().over(Window.order_by("-score")).as_("rank")
).from_("students")

# If two students have score 95, both get rank 1, next student gets rank 3
```

### DENSE_RANK()

Like RANK, but without gaps in ranking.

```python
query = Q.select(
    "name",
    "score",
    func.dense_rank().over(Window.order_by("-score")).as_("rank")
).from_("students")

# If two students have score 95 (rank 1), next student gets rank 2 (not 3)
```

### NTILE(n)

Divides rows into n buckets as evenly as possible.

```python
# Divide employees into 4 quartiles by salary
query = Q.select(
    "name",
    "salary",
    func.ntile(4).over(Window.order_by("-salary")).as_("quartile")
).from_("employees")
```

## Value Functions

### LAG()

Access data from a previous row in the result set.

```python
# Compare each day's value with the previous day
query = Q.select(
    "date",
    "value",
    func.lag("value", 1).over(Window.order_by("date")).as_("prev_value")
).from_("metrics")

# SQL: SELECT `date`, `value`,
#   LAG(`value`, 1) OVER (ORDER BY `date` ASC) AS `prev_value`
# FROM `metrics`

# Calculate day-over-day change
query = Q.select(
    "date",
    "value",
    Raw("value - LAG(value, 1) OVER (ORDER BY date)").as_("change")
).from_("metrics")
```

### LEAD()

Access data from a following row in the result set.

```python
# Compare current value with next value
query = Q.select(
    "date",
    "value",
    func.lead("value", 1).over(Window.order_by("date")).as_("next_value")
).from_("metrics")
```

### FIRST_VALUE()

Returns the first value in the window frame.

```python
# Compare each employee's salary to the highest in their department
query = Q.select(
    "name",
    "department",
    "salary",
    func.first_value("salary").over(
        Window.partition_by("department").and_order_by("-salary")
    ).as_("max_dept_salary")
).from_("employees")
```

### LAST_VALUE()

Returns the last value in the window frame.

```python
# Get the last recorded value for each partition
query = Q.select(
    "date",
    "category",
    "value",
    func.last_value("value").over(
        Window.partition_by("category")
        .and_order_by("date")
        .rows_between("UNBOUNDED PRECEDING", "UNBOUNDED FOLLOWING")
    ).as_("final_value")
).from_("measurements")
```

## Aggregate Functions with OVER

Any aggregate function can be used as a window function with the `over()` method.

### Running Totals

```python
# Calculate running total of sales
query = Q.select(
    "date",
    "amount",
    func.sum("amount").over(
        Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")
    ).as_("running_total")
).from_("transactions")
```

### Moving Averages

```python
# 7-day moving average
query = Q.select(
    "date",
    "value",
    func.avg("value").over(
        Window.order_by("date").rows_between("6 PRECEDING", "CURRENT ROW")
    ).as_("moving_avg_7d")
).from_("metrics")
```

### Percentage of Total

```python
# Calculate each sale as percentage of department total
query = Q.select(
    "salesperson",
    "department",
    "amount",
    Raw("amount / SUM(amount) OVER (PARTITION BY department) * 100").as_("pct_of_dept")
).from_("sales")
```

## Frame Clauses

Frame clauses define the exact subset of rows within the partition to consider.

### ROWS BETWEEN

Defines frames based on physical row positions.

```python
# Last 3 rows including current
window = Window.order_by("date").rows_between("2 PRECEDING", "CURRENT ROW")

# Current row and next 2 rows
window = Window.order_by("date").rows_between("CURRENT ROW", "2 FOLLOWING")

# All rows from start to current
window = Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "CURRENT ROW")

# All rows in partition
window = Window.order_by("date").rows_between("UNBOUNDED PRECEDING", "UNBOUNDED FOLLOWING")
```

### RANGE BETWEEN

Defines frames based on value ranges (useful for time-based windows).

```python
# All rows with same ORDER BY value
window = Window.order_by("date").range_between("CURRENT ROW", "CURRENT ROW")

# From start to current value
window = Window.order_by("score").range_between("UNBOUNDED PRECEDING", "CURRENT ROW")
```

## Common Use Cases

### Top N per Group

```python
# Get top 3 highest-paid employees per department
from sqlo import Condition

subquery = Q.select(
    "name",
    "department",
    "salary",
    func.row_number().over(
        Window.partition_by("department").and_order_by("-salary")
    ).as_("rn")
).from_("employees")

query = (
    Q.select("name", "department", "salary")
    .from_(subquery.as_("ranked"))
    .where("rn <=", 3)
)
```

### Gap Detection

```python
# Find gaps in sequential IDs
query = Q.select(
    "id",
    func.lag("id", 1).over(Window.order_by("id")).as_("prev_id"),
    Raw("id - LAG(id, 1) OVER (ORDER BY id)").as_("gap")
).from_("records")
```

### Running Difference

```python
# Track change from previous period
query = Q.select(
    "month",
    "revenue",
    Raw("revenue - LAG(revenue, 1) OVER (ORDER BY month)").as_("change"),
    Raw("(revenue - LAG(revenue, 1) OVER (ORDER BY month)) / LAG(revenue, 1) * 100").as_("pct_change")
).from_("monthly_sales")
```

### Year-over-Year Comparison

```python
# Compare sales to same month last year
query = Q.select(
    "month",
    "year",
    "sales",
    func.lag("sales", 12).over(Window.order_by("month")).as_("sales_last_year"),
    Raw("(sales - LAG(sales, 12) OVER (ORDER BY month)) / LAG(sales, 12) * 100").as_("yoy_growth")
).from_("monthly_data")
```

## Performance Considerations

### Index Usage

Window functions benefit from indexes on:
- `PARTITION BY` columns
- `ORDER BY` columns

```sql
-- Recommended indexes
CREATE INDEX idx_emp_dept_salary ON employees(department, salary DESC);
CREATE INDEX idx_sales_date ON sales(date);
```

### Avoid Redundant Windows

```python
# ❌ Bad: Creates window specification multiple times
query = Q.select(
    func.row_number().over(Window.partition_by("dept").and_order_by("-salary")).as_("rank"),
    func.dense_rank().over(Window.partition_by("dept").and_order_by("-salary")).as_("dense_rank")
).from_("employees")

# ✅ Better: With CTEs, the window is evaluated once
# (Though current sqlo doesn't support named windows in the WINDOW clause)
```

### Limit Result Sets

```python
# Use WHERE to filter before window functions when possible
query = (
    Q.select(
        "name",
        "department", 
        "salary",
        func.rank().over(Window.partition_by("department").and_order_by("-salary")).as_("rank")
    )
    .from_("employees")
    .where("active", True)  # Filter first
    .where("hire_date >", "2020-01-01")
)
```

## Debugging

Use the debug mode to see generated SQL:

```python
query = Q.select(
    "name",
    func.row_number().over(Window.partition_by("department").and_order_by("-salary")).as_("rank")
).from_("employees").debug()

sql, params = query.build()
# Prints the SQL with window function
```

## See Also

- [SELECT Queries](select.md) - Using window functions in SELECT
- [Expressions & Functions](expressions.md) - Available SQL functions
- [Condition Objects](conditions.md) - Filtering results
