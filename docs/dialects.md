# Dialects

sqlo builds SQL for **MySQL** (the default) and **PostgreSQL**. A dialect decides how
identifiers are quoted, which syntax is used for features that differ between databases, and
which features exist at all.

A feature a dialect does not have raises `UnsupportedFeatureError` when you use it, instead of
producing SQL that fails, or means something else, on that database.

## Tested versions

The SQL sqlo generates is run on real servers by the [integration tests](https://github.com/nan-guo/sqlo/blob/main/DEVELOPMENT.md#integration-tests):

| Database | Versions tested |
| --- | --- |
| MySQL | 8.0, 8.4 |
| PostgreSQL | 15, 16, 17 |

Older versions are not tested. Window functions and CTEs, which sqlo can generate, exist only from
MySQL 8.0.

## Choosing a dialect

`Q.using(dialect)` returns a factory for one dialect. Several can be used side by side, and
the global default is not touched:

```python
from sqlo import MySQLDialect, PostgreSQLDialect, Q

pg = Q.using(PostgreSQLDialect())
mysql = Q.using(MySQLDialect())

pg.select("id").from_("users").where("active", True).build()
# ('SELECT "id" FROM "users" WHERE "active" = %s', (True,))

mysql.select("id").from_("users").where("active", True).build()
# ('SELECT `id` FROM `users` WHERE `active` = %s', (True,))
```

`Q.select(...)` and the other `Q` methods use the global default, which is MySQL unless you call
`Q.set_dialect(PostgreSQLDialect())`. Pass a dialect **instance**, not the class.

Both dialects use the `%s` placeholder, which is what psycopg, pymysql and aiomysql expect.
Numbered placeholders (`$1`) and `?` are not supported.

### Subqueries must use the same dialect

A subquery built for one dialect cannot be used in a query built for another, because it would
bring its own quoting into the statement. This applies to `where_in`, `FROM` and `JOIN` subqueries,
`union`, CTEs, `INSERT ... SELECT` and `Condition.exists`:

```python
sub = mysql.select("id").from_("orders")
pg.select("*").from_("users").where_in("id", sub).build()
# ValueError: A subquery built for the MySQL dialect cannot be used in a query built for the
# PostgreSQL dialect
```

## What each dialect supports

| Feature | MySQL | PostgreSQL |
| --- | --- | --- |
| Identifier quoting | `` `name` `` | `"name"` (case-sensitive, see below) |
| `INNER`, `LEFT`, `RIGHT`, `CROSS` joins | yes | yes |
| `FULL [OUTER]` join | **no** | yes |
| Subqueries, `UNION`, CTEs, window functions | yes | yes |
| `JSON(col).extract(path)` | `` `d`->>'$.a.b' ``, wildcards allowed | `"d" #>> '{a,b}'`, **no wildcards** |
| `force_index`, `use_index`, `ignore_index` | yes | **no** |
| `optimizer_hint` | yes | **no** |
| `on_conflict(...).do_update(...)` | `ON DUPLICATE KEY UPDATE` (conflict columns are ignored) | `ON CONFLICT (cols) DO UPDATE` (conflict columns required) |
| `on_conflict(...).do_nothing()` | no-op `ON DUPLICATE KEY UPDATE` | `ON CONFLICT [(cols)] DO NOTHING` |
| `.ignore()`, `on_duplicate_key_update()` | yes | **no**: use `on_conflict()` |
| `UPDATE` / `DELETE` with a join | yes (not together with `ORDER BY` or `LIMIT`) | **no** |
| `UPDATE` / `DELETE` with `ORDER BY` or `LIMIT` | yes (not together with a join) | **no** |
| Operators `<=>`, `REGEXP`, `NOT REGEXP` | yes | **no** |
| Operators `~`, `~*`, `!~`, `!~*`, `ILIKE`, `NOT ILIKE`, `IS [NOT] DISTINCT FROM` | **no** | yes |
| Window frame interval | `INTERVAL 7 DAY PRECEDING` | `INTERVAL '7 day' PRECEDING` |

The window frame interval is written the MySQL way in your code, `INTERVAL 7 DAY PRECEDING`, and
rendered for the dialect. PostgreSQL has no `QUARTER` unit, so `n` quarters become `3n` months.

### Unsupported features

```python
from sqlo import UnsupportedFeatureError

try:
    pg.select("*").from_("users").force_index("idx_email")
except UnsupportedFeatureError as error:
    print(error)
# Index hints is not supported by the PostgreSQL dialect.

pg.insert_into("users").values({"id": 1}).ignore()
# UnsupportedFeatureError: INSERT IGNORE is not supported by the PostgreSQL dialect.
# Use on_conflict().do_nothing() instead.
```

`UnsupportedFeatureError` is a `ValueError`. It is raised when the method is called, not when
`build()` runs, so the traceback points at the line that needs to change.

The operators are checked when the query is built for a dialect: a `Condition` can be created without
knowing the dialect, and `Condition("a REGEXP", "x").build(dialect)` raises for PostgreSQL.

## Writing code that runs on both

- **Use `on_conflict()`** for upserts, see [INSERT](insert.md#portable-upsert-on_conflict). Pass the
  conflict columns so that it works on PostgreSQL.
- **Use `Condition`, `where`, `where_in`, `where_like` and the standard operators**: these render the
  same on both. Reach for `ILIKE`, `~` or `REGEXP` only when the code is tied to one database.
- **Give every subquery in `FROM` and `JOIN` an alias.** sqlo requires it on both: MySQL needs it, and
  PostgreSQL before 16 does too.
- **`offset()` needs `limit()`** on both. MySQL requires it; sqlo applies the same rule to PostgreSQL.
- **Pass a `LIMIT` and `ORDER BY` only to `SELECT`.** `UPDATE` and `DELETE` with a join, `ORDER BY` or
  `LIMIT` exist only in MySQL. To limit an update on PostgreSQL, select the ids first and use
  `where_in(ids)` or a subquery.

## Differences that are not sqlo's to hide

These are rules of the databases. They are the same whether you use sqlo or write the SQL yourself.

- **A `SELECT` alias in `HAVING`.** MySQL allows `HAVING n > 1` when `n` is `COUNT(*) AS n`;
  PostgreSQL does not (`column "n" does not exist`). Write the expression, which works on both:
  `.having(Raw("COUNT(*) > %s", [1]))`. An alias in `WHERE` is not allowed by either, and an alias in
  `ORDER BY` is allowed by both.
- **Quoted names are case-sensitive in PostgreSQL.** sqlo quotes every identifier exactly as you wrote
  it, so `Users` and `users` are different tables there. Use the same case the table was created with.
- **Upserts with an expression.** In PostgreSQL a column inside a `Raw` expression of `do_update` must be
  qualified with the table: `Raw('"visits"."count" + %s', [1])`. An unqualified name is ambiguous with the
  `excluded` row.
- **`->>` and `#>>` return text.** Comparing a JSON value with a number needs a cast on both
  databases, for example `Raw`.
- **PostgreSQL is stricter about types.** `integer = boolean` is an error, so pass the type the column has.
- **`INSERT IGNORE` hides errors.** It also swallows a value that is too long for its column, which
  is why `on_conflict().do_nothing()` is a no-op update on MySQL and reports it.

## Writing your own dialect

Subclass `Dialect` and implement `quote_char` and `parameter_placeholder()`. Everything else defaults
to the portable subset of SQL, and anything MySQL- or PostgreSQL-specific raises
`UnsupportedFeatureError`. Turn features on by overriding the capability attributes and the hooks:

```python
from sqlo.dialects.base import Dialect

class SQLiteDialect(Dialect):
    supports_on_conflict = True       # on_conflict() is available
    conflict_target_required = True   # do_update() needs the conflict columns

    @property
    def quote_char(self):
        return '"'

    def parameter_placeholder(self):
        return "?"

    def inserted_value(self, quoted_column):          # what values_of("col") renders to
        return f"excluded.{quoted_column}"

    def conflict_clause(self, target, assignments, first_column):
        on = f" ON CONFLICT ({', '.join(target)})" if target else " ON CONFLICT"
        if assignments is None:
            return f"{on} DO NOTHING"
        return f"{on} DO UPDATE SET {', '.join(assignments)}"
```

| Capability attribute | Default | Meaning |
| --- | --- | --- |
| `join_types` | `INNER`, `LEFT`, `RIGHT`, `CROSS` (+ `OUTER` forms) | Allowed join types; add `FULL` and `FULL OUTER` if supported |
| `extra_operators` | none | Comparison operators beyond the portable ones |
| `supports_insert_ignore` | no | `.ignore()` |
| `supports_on_duplicate_key` | no | `on_duplicate_key_update()` |
| `supports_on_conflict` | no | `on_conflict()`; also implement `conflict_clause` and `inserted_value` |
| `conflict_target_required` | no | `do_update()` must name the conflict columns |
| `supports_dml_join` | no | Joins in `UPDATE` and `DELETE` |
| `supports_dml_order_limit` | no | `ORDER BY` and `LIMIT` in `UPDATE` and `DELETE` |

The hooks `index_hint`, `optimizer_hint`, `json_extract`, `inserted_value`, `conflict_clause` and
`window_frame_bound` return the SQL fragment for the dialect. Only the portable operators
and the operators sqlo already knows (MySQL's and PostgreSQL's) can be enabled through `extra_operators`.

The built-in dialects are tested on real servers; a dialect you write is only as good as the tests you give it.
