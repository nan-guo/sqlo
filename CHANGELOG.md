# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.0.0] - Unreleased

1.0.0 adds PostgreSQL next to MySQL, closes a number of SQL injection and silent-data-loss
problems, and runs the SQL it generates against real MySQL and PostgreSQL servers in its tests.
It changes behaviour in places where the old behaviour was wrong, so **read the first two sections
before upgrading from 0.2.x.**

### Silent changes: review these first

These do **not** raise an error. The code keeps running and does something different.

- **Strings in `on_duplicate_key_update` are now data, not SQL.** `{"n": "n + 1"}` used to be written as the
  expression `n + 1` (any string containing `+ - * /`, `VALUES(` or `NOW()` was treated as SQL). It is now
  bound as the *text* `'n + 1'`. Use `Raw` for an expression and `values_of()` for the inserted value:

  ```python
  # before
  .on_duplicate_key_update({"n": "n + 1", "name": "VALUES(name)", "seen": "NOW()"})
  # after
  .on_duplicate_key_update({"n": Raw("`n` + 1"), "name": values_of("name"), "seen": Raw("NOW()")})
  ```

- **`limit(0)` is emitted.** `UPDATE ... LIMIT 0` and `DELETE ... LIMIT 0` used to drop the `LIMIT` clause and
  affect every matching row. They now write `LIMIT 0`.
- **`ORDER BY`, `LIMIT` and `OFFSET` of a query with `union()` apply to the whole union.** They used to be written
  before the `UNION`, which MySQL rejects. To limit only the first query, wrap it:
  `Q.select("id").from_(first.limit(5).as_("t")).union(second)`. A query passed to `union()` that has its own
  `ORDER BY` or `LIMIT` is wrapped in parentheses.
- **`as_()` no longer aliases the query's own `FROM` table.** `Q.select("id").from_("users").as_("a")` used to write
  `FROM users a` inside the subquery, which broke `users.id` references. `as_()` now names the query for the query
  that embeds it; use `from_("users", "a")` for the table alias. An explicit `from_(subquery, alias="z")` now wins
  over the subquery's own alias, and the outer query no longer inherits it.
- **`Condition` renders qualified columns correctly.** `Condition("u.age>", 1)` wrote `` `u.age` `` (one identifier,
  wrong in MySQL); it now writes `` `u`.`age` ``, like `where()` always did.
- **`Condition` and `values_of` changed shape.** `Condition.parts` is gone, `Condition.build(dialect)` now uses the
  dialect it is given (it defaults to `Q.get_dialect()`), `Condition.exists(subquery)` builds the subquery when the
  condition is rendered (in `where()` or `build()`), and `values_of()` returns an `Inserted` node instead of a `Raw` with MySQL text (no `.sql`).
- **Debug mode uses `logging`.** `Q.set_debug(True)` prints the same lines, but the output is now produced by the
  `sqlo` and `sqlo.params` loggers. It also applies to queries created *before* the call (it used to apply only to
  queries created after it). `Q._debug` no longer exists.
- **Custom `Dialect` subclasses lose the MySQL extras.** The new capability attributes default to the portable subset,
  so a custom dialect no longer gets `<=>`/`REGEXP`, index and optimizer hints, `INSERT IGNORE`,
  `ON DUPLICATE KEY UPDATE`, JOINs in `UPDATE`/`DELETE` or `ORDER BY`/`LIMIT` in `UPDATE`/`DELETE` unless it turns them
  on (see [Dialects](docs/dialects.md#writing-your-own-dialect)). Using one raises `UnsupportedFeatureError`.

### Breaking changes: used to be accepted, now raise

Each of these used to produce SQL that was injectable, invalid, wrong, or that lost data.

| You wrote | Now | Use instead |
| --- | --- | --- |
| `where("age MY_OP", 10)`, any operator outside the known set | `ValueError` | `where(Raw("age MY_OP %s", [10]))` |
| `func.count("DISTINCT id")`, any function argument that is not a column or `*` | `ValueError` | `func.count(Raw("DISTINCT id"))` |
| `join(t, "s.user_id = u.id AND s.status = 'active'")`: a string `ON` with a literal, function, `OR` or parentheses | `ValueError` | `join(t, Condition("s.user_id", Raw("u.id")) & Condition("s.status", "active"))` or `Raw(...)` |
| `join(t, on=<anything but str, Raw, Condition>)` | `TypeError` | (it used to write the object's repr into the SQL) |
| `with_("SELECT ...", "c")`: a string CTE | `TypeError` | `with_(Raw("SELECT ..."), "c")` |
| `from_(subquery)` with no alias | `ValueError` | `subquery.as_("s")` or `from_(subquery, alias="s")` |
| `join(..., join_type="FULL OUTER")` on MySQL | `UnsupportedFeatureError` | PostgreSQL, or a `LEFT JOIN` plus `UNION` |
| `limit("10")`, `offset(-1)`, `paginate(1, 0)` | `TypeError` / `ValueError` | pass non-negative ints, `per_page >= 1` |
| `offset(20)` without `limit()` | `ValueError` | `limit(10).offset(20)` |
| `Condition("deleted_at", None)`, `Condition("a")` | `ValueError` | `Condition.null("deleted_at")` |
| `where_like("name", None)` (all query types) | `ValueError` | `where_null("name")` |
| `where(Condition())`, `Condition.or_()` passed to `where` | `ValueError` | (an empty condition is skipped when combined with `&` / `\|`) |
| `values([{"a": 1, "b": 2}, {"a": 3}])`: rows with different columns | `ValueError` | give every row the same keys |
| `batch_update` with rows that differ, or a repeated key | `ValueError` | same keys in every row, unique key values |
| `update(...).join(...).limit(n)` / `.order_by(...)`, same for `delete_from` | `ValueError` | MySQL forbids it; use `where_in(ids)` |
| `optimizer_hint("... */ ...")` | `ValueError` | a hint without `/*` or `*/` |
| identifiers such as `a..b`, `a.` or `users\n`; JSON paths with quoted keys; window frame bounds outside the documented forms | `ValueError` | valid identifiers, `a.b[0].c` paths, `UNBOUNDED PRECEDING` / `CURRENT ROW` / `<n> PRECEDING` / `INTERVAL <n> <unit> PRECEDING` |
| a MySQL-only feature on PostgreSQL (`force_index`, `optimizer_hint`, `ignore()`, `on_duplicate_key_update`, JOIN or `ORDER BY`/`LIMIT` in `UPDATE`/`DELETE`, `<=>`, `REGEXP`), and a PostgreSQL-only operator on MySQL | `UnsupportedFeatureError` | see [Dialects](docs/dialects.md) |

Also: a subquery built for one dialect cannot be used in a query built for another (`ValueError`), and
`values_of()` takes a plain column name (`values_of("t.name")` raises `ValueError`).

### Added

- **PostgreSQL dialect**: `PostgreSQLDialect`, with `"` quoting, `FULL [OUTER]` joins, the operators `~ ~* !~ !~* ILIKE
  NOT ILIKE IS [NOT] DISTINCT FROM`, JSON paths as `->>` and `#>>`, and window frame intervals as `INTERVAL '7 day'`.
- **`Q.using(dialect)`** returns a `QueryFactory` bound to one dialect, so MySQL and PostgreSQL queries can be built
  side by side. `MySQLDialect`, `PostgreSQLDialect` and `QueryFactory` are exported from `sqlo`.
- **`UnsupportedFeatureError`** (a `ValueError`) is raised, when the method is called, for a feature the dialect
  does not have.
- **`on_conflict(*columns).do_update({...})` / `.do_nothing()`**: a portable upsert. MySQL renders
  `ON DUPLICATE KEY UPDATE`, PostgreSQL renders `ON CONFLICT (...) DO UPDATE / DO NOTHING`. `values_of("col")` is the
  inserted value (`VALUES(col)` / `EXCLUDED.col`).
- **`Query.clone()`** copies a query, including nested queries, so one base query can be branched safely.
- **`Raw` in `Condition`**: `Condition(Raw("MATCH(t) AGAINST(%s)", ["x"]))` is a complete predicate, and
  `Condition(Raw("LENGTH(p)"), 8, ">")` uses an expression on the left.
- **`join(..., on=...)` accepts `Raw` and `Condition`**, with their parameters, in `SELECT`, `UPDATE` and `DELETE`.
  `with_()` accepts `Raw`.
- **Dialect extension points**: the capability attributes `join_types`, `extra_operators`, `supports_insert_ignore`,
  `supports_on_duplicate_key`, `supports_on_conflict`, `conflict_target_required`, `supports_dml_join`,
  `supports_dml_order_limit`, and the hooks `index_hint`, `optimizer_hint`, `json_extract`, `inserted_value`,
  `conflict_clause`, `window_frame_bound`.
- **Debug output through `logging`**: the `sqlo` logger carries the SQL and `sqlo.params` the parameters, so the
  values can be silenced on their own. `Q.set_debug(True, hide_params=True)` leaves them out.
- Validation helpers in `sqlo.security`: `require_identifier`, `validate_alias`, `validate_operator`,
  `validate_non_negative_int`.

### Fixed

- `UPDATE`/`DELETE` with `limit(0)` dropped the `LIMIT` and hit every matching row.
- `Condition(col, None)` was dropped silently and produced `WHERE ()`; an empty `IN ()` was invalid SQL (it is now
  `FALSE`, and `NOT IN ()` is `TRUE`).
- `Condition & ComplexCondition` raised `AttributeError`, and an empty condition in `&`, `|` or `or_()` produced
  invalid SQL such as `(AND ...)` or `( OR )`.
- `DELETE ... JOIN` was invalid MySQL (`DELETE FROM t INNER JOIN ...`); it now writes `DELETE t FROM t INNER JOIN ...`.
- `UPDATE`/`DELETE` joins did not bind the parameters of their `ON` clause, and joining a subquery wrote neither
  parentheses, `AS` nor its parameters.
- `INSERT` with rows that had different columns inserted `NULL` for a missing column and dropped an extra one.
- `batch_update` raised `KeyError` for rows with different columns and let a repeated key pass.
- `OFFSET` without `LIMIT` was ignored and returned the wrong rows.
- `where_in("bad name", [])` skipped the identifier check, and `where_like("a >", "x")` silently turned `LIKE` into `>`.
- Nested `Func` arguments, `Raw` as a CTE or as a join condition, and a `Raw` in a `Condition` wrote the object's repr
  or nothing at all.
- `UNION` with `ORDER BY` or `LIMIT` produced invalid SQL.
- The debug flag was captured when a query was created.

### Security

The inputs below were written into the SQL without being checked. If you passed untrusted values to any of them
in 0.2.x, upgrade; they now raise instead.

- the `operator` argument of `where`, `or_where` and `having`, and the operator inside `"col op"` strings
- column names in `Condition`
- `limit`, `offset` and `paginate` values
- the table, alias and type of a join, and `from_` / `as_` aliases
- string values of `on_duplicate_key_update` that contained `+ - * /`, `VALUES(` or `NOW()`
- function names and arguments, JSON paths, and window frame bounds
- `optimizer_hint` text containing `*/`, which ended the hint comment and ran the rest as SQL
- string `ON` conditions of a join, and string CTEs
- identifiers with a trailing newline

`Raw` is still written as-is, by design. [Security](docs/security.md#where-trusted-sql-is-accepted) lists every place
that accepts trusted SQL and what each one checks.

### Performance

Measured with micro-benchmarks on the maintainer's machine, so treat them as relative.

- Quoted identifiers are cached (a bounded cache): `quote()` went from 1.19 to 0.11 µs, a simple `SELECT` build from
  5.7 to 2.6 µs, a complex one from 17.6 to 7.9 µs, `UPDATE` from 5.2 to 2.1 µs and `DELETE` from 3.2 to 1.6 µs.
- `clone()` took 5.8 µs for a mid-size query against 15.9 µs for `copy.deepcopy`, and does not grow with the size of
  an `IN` list.
- Costs: building a `Condition` on its own with `build()` is about 0.8 µs slower, because it now renders when built;
  the dialect checks and the debug level check add about 0.05 to 0.1 µs to a build.

### Documentation

- New [Dialects](docs/dialects.md) guide: what MySQL and PostgreSQL support, writing code that runs on both, the
  differences that are the databases' own, and writing a dialect.
- [Security](docs/security.md) lists where trusted SQL is accepted and warns that debug output can contain secrets.
- [INSERT](docs/insert.md) covers `on_conflict()`, [JOIN](docs/joins.md) the rules for `ON`, and
  [SELECT](docs/select.md) the `AND`/`OR` precedence, `clone()` and the two kinds of alias.
- Several examples that did not work (for instance `Condition(Raw(...), ">", 8)`) were corrected, and the examples
  that passed literals or functions in a string `ON` condition now use `Condition` or `Raw`.

### Development

- `tests/integration/` runs the generated SQL on real MySQL and PostgreSQL servers (95 tests, skipped unless
  `SQLO_TEST_MYSQL_URL` and `SQLO_TEST_POSTGRES_URL` are set). The cases that are not tied to one dialect run on both
  databases and must return the same rows. They pass on MySQL 8.0 and 8.4 and on PostgreSQL 15, 16 and 17.
- `make db-up`, `make test-integration`, `make db-down`; a CI `integration` job with MySQL 8.4 and PostgreSQL 17
  services; `pymysql` and `psycopg[binary]` as `dev` dependencies only (runtime dependencies stay at zero).
- Unit tests went from 260 to 1,133; coverage is 99%.

### Known limitations

- Numbered placeholders (`$1`) and `?` are not supported: both dialects use `%s`.
- `RETURNING` is not supported.
- `UPDATE` and `DELETE` with a join, `ORDER BY` or `LIMIT` are not translated for PostgreSQL (`UPDATE ... FROM`,
  `DELETE ... USING`); they raise `UnsupportedFeatureError`.
- Only MySQL 8.0 and 8.4 and PostgreSQL 15 to 17 are tested.
- `INSERT ... VALUES` does not check a misplaced `values_of()` cell by cell, because that would make bulk inserts
  slower; the database driver rejects the object.


## [0.2.1] - 2025-12-04

### Documentation
- **Comprehensive Documentation Expansion**: Added 7 new documentation files (3,300+ lines)
  - `window-functions.md` - Complete guide to window functions with examples and use cases
  - `cte.md` - Common Table Expressions including recursive CTEs
  - `json.md` - JSON support with MySQL JSON functions
  - `batch-operations.md` - Efficient bulk operations guide
  - `troubleshooting.md` - Comprehensive troubleshooting and debugging guide
  - `integration-aiomysql.md` - Complete async integration guide with aiomysql
  - `recipes.md` - Best practices and common patterns
- Updated `docs/index.rst` with new documentation structure and sections

### Code Quality
- Enhanced type hints in `window.py` with proper return type annotations
- All mypy checks now pass without notes or warnings

## [0.2.0] - 2025-12-03

### Added
- **Window Functions Support**: Full support for SQL window functions with `Window` class
  - `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, `NTILE()` ranking functions
  - `LAG()`, `LEAD()`, `FIRST_VALUE()`, `LAST_VALUE()` value functions
  - Aggregate functions with OVER clause: `SUM()`, `AVG()`, `COUNT()`, `MIN()`, `MAX()`
  - `PARTITION BY` and `ORDER BY` clauses
  - Frame clauses: `ROWS BETWEEN` and `RANGE BETWEEN`
- **CTE (Common Table Expressions) Support**: Build complex queries with WITH clause
  - `with_()` method for adding CTEs to any query type
  - Support for recursive CTEs
  - Multiple CTEs in a single query
- **JSON Field Support**: Query and filter JSON columns
  - `JSON` class for JSON column operations
  - `JSONPath` for extracting JSON values with `->>'$.path'` syntax
  - Support in both SELECT and WHERE clauses
- **Batch UPDATE Optimization**: Efficient bulk updates using CASE WHEN
  - `batch_update()` method for updating multiple rows with different values
  - Automatic generation of optimized CASE WHEN SQL
- **Debug Mode**: Print SQL queries and parameters for debugging
  - `Q.set_debug(True)` to enable global debug mode
  - `query.debug()` for per-query debugging
- **Type Hints Improvements**: Enhanced IDE support with Generic types
  - `SelectQuery[T]` for better type inference
  - Improved autocomplete for query results

### Performance
- **Parameter Placeholder Caching**: Cache dialect parameter placeholders to reduce function calls

### Changed
- Exported `JSON`, `JSONPath`, and `Window` classes in main `__init__.py`
- Updated `Func` class with `over()` method for window functions
- Enhanced `SelectQuery` to handle `WindowFunc` and `JSONPath` expressions

### Documentation
- Added comprehensive examples for all new features in README
- Created detailed walkthrough documentation
- Added unit tests for all new features (17 new tests)

## [0.1.0] - 2025-11-29

### Security
- **Breaking Change**: Mandatory identifier validation for table and column names. Invalid identifiers now raise `ValueError`.
- **Breaking Change**: `UPDATE` and `DELETE` queries now require a `WHERE` clause or an explicit `.allow_all_rows()` call to prevent accidental mass operations.
- **Breaking Change**: `Raw()` expressions now enforce string type for the SQL argument.
- Implemented safe handling for empty lists in `WHERE IN` clauses (generates `WHERE FALSE` or `WHERE TRUE`).
- Added validation for table names in `JOIN` clauses.
- Added comprehensive security test suite covering SQL injection vectors and edge cases.

### Documentation
- Completely rewrote `docs/security.md` with detailed security guides and best practices.
- Updated `docs/update.md` and `docs/delete.md` with safety warnings and `allow_all_rows()` usage.
- Added documentation for `Condition.null()` and `Condition.not_null()` factory methods.
- Added `make docs` and `make docs-serve` targets for local documentation building.
- Added GitHub Actions workflow for automatic documentation deployment to GitHub Pages.

## [0.0.1] - 2025-11-28

### Added
- Initial release of `sqlo`.
- Support for SELECT, INSERT, UPDATE, DELETE queries.
- MySQL dialect support.
- Type-safe query building API.
- Comprehensive test coverage (99%).
- Code quality tools: ruff, mypy, xenon, bandit.
