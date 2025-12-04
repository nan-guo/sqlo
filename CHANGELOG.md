# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
