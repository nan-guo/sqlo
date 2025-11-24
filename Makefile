.PHONY: install format lint check test coverage clean

# Install dependencies
install:
	uv sync --all-extras

# Format code with ruff
format:
	uv run ruff format .

# Lint code with ruff
lint:
	uv run ruff check .

# Lint and auto-fix
lint-fix:
	uv run ruff check --fix .

# Type check with mypy
typecheck:
	uv run mypy src/

# Run all checks (format + lint + typecheck)
check: format lint typecheck

# Run tests
test:
	uv run pytest

# Run tests with coverage
coverage:
	uv run pytest --cov=sqlo --cov-report=html --cov-report=term

# Test against multiple Python versions (requires pyenv or similar)
test-all-versions:
	@echo "Testing Python 3.9..."
	@uv run --python 3.9 pytest || echo "Python 3.9 not available"
	@echo "Testing Python 3.10..."
	@uv run --python 3.10 pytest || echo "Python 3.10 not available"
	@echo "Testing Python 3.11..."
	@uv run --python 3.11 pytest || echo "Python 3.11 not available"
	@echo "Testing Python 3.12..."
	@uv run --python 3.12 pytest || echo "Python 3.12 not available"
	@echo "Testing Python 3.13..."
	@uv run --python 3.13 pytest || echo "Python 3.13 not available"

# Install pre-commit hooks
pre-commit-install:
	uv run pre-commit install

# Run pre-commit on all files
pre-commit-run:
	uv run pre-commit run --all-files

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
