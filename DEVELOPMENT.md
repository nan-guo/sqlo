# Development Workflow

## Using uv (Recommended)

uv doesn't require scripts configuration. Just use `uv run` directly:

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=sqlo --cov-report=html

# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type check
uv run mypy src/

# Install dependencies
uv sync --all-extras
```

## Using Makefile (Simpler)

We've created a Makefile for convenience:

```bash
# Run tests
make test

# Run tests with coverage
make coverage

# Format code
make format

# Lint code
make lint

# Auto-fix linting issues
make lint-fix

# Type check
make typecheck

# Run all checks (format + lint + typecheck)
make check

# Run the generated SQL on real MySQL and PostgreSQL (needs Docker)
make db-up
make test-integration
make db-down

# Install pre-commit hooks
make pre-commit-install

# Clean build artifacts
make clean
```

## Recommendation

- **For quick commands**: Use `uv run <command>`
- **For complex workflows**: Use `make <target>`
- **For CI/CD**: Use `uv run` directly

Example CI/CD workflow:
```yaml
- run: uv sync --all-extras
- run: uv run ruff format --check .
- run: uv run ruff check .
- run: uv run mypy src/
- run: uv run pytest --cov=sqlo
```

## Integration tests

`tests/integration/` runs the SQL sqlo generates on real MySQL 8.4 and PostgreSQL 17
servers and checks the rows that come back. The tests that are not tied to one dialect run
on both databases and must give the same result.

They are skipped unless the servers are configured, so a plain `pytest` needs no database:

```bash
export SQLO_TEST_MYSQL_URL=mysql://user:password@127.0.0.1:3306/dbname
export SQLO_TEST_POSTGRES_URL=postgresql://user:password@127.0.0.1:5432/dbname
uv run pytest tests/integration
```

`make db-up` starts both servers in Docker with matching settings, `make test-integration`
runs the tests against them and `make db-down` removes them. The tests create the tables `u`,
`v`, `o` and `w` in the given database, so point them at a scratch database, and every test runs
in a transaction that is rolled back. CI runs them in the `integration` job.
