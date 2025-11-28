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
