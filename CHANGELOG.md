# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
