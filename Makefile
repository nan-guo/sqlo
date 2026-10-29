.PHONY: install format lint check test coverage clean docs docs-serve db-up db-down test-integration

# Install dependencies
install:
	uv sync --all-extras

# Format code (imports and sources)
format:
	uv run ruff check --select I --fix .
	uv run ruff format .

# Check code style (format, lint, types)
style:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src/

# Check code complexity
complexity:
	uv run xenon --max-absolute C --max-modules C --max-average B src

# Check security issues
security:
	uv run bandit -c pyproject.toml -r src

# Run all checks (alias for style)
check: style

# Run tests
test:
	uv run pytest --cov=sqlo --cov-report=term-missing

# Throwaway MySQL and PostgreSQL servers for the integration tests (needs Docker)
SQLO_MYSQL_PORT ?= 53306
SQLO_POSTGRES_PORT ?= 55432
SQLO_TEST_MYSQL_URL ?= mysql://root:sqlo@127.0.0.1:$(SQLO_MYSQL_PORT)/sqlo
SQLO_TEST_POSTGRES_URL ?= postgresql://postgres:sqlo@127.0.0.1:$(SQLO_POSTGRES_PORT)/postgres

db-up:
	docker run -d --name sqlo-test-mysql -e MYSQL_ROOT_PASSWORD=sqlo -e MYSQL_DATABASE=sqlo \
		-p 127.0.0.1:$(SQLO_MYSQL_PORT):3306 mysql:8.4
	docker run -d --name sqlo-test-postgres -e POSTGRES_PASSWORD=sqlo \
		-p 127.0.0.1:$(SQLO_POSTGRES_PORT):5432 postgres:17-alpine
	@echo "Started MySQL on port $(SQLO_MYSQL_PORT) and PostgreSQL on port $(SQLO_POSTGRES_PORT)."
	@echo "They need a few seconds to accept connections before 'make test-integration'."

db-down:
	-docker rm -f sqlo-test-mysql sqlo-test-postgres

# Run the SQL sqlo generates on real MySQL and PostgreSQL (after 'make db-up')
test-integration:
	SQLO_TEST_MYSQL_URL=$(SQLO_TEST_MYSQL_URL) SQLO_TEST_POSTGRES_URL=$(SQLO_TEST_POSTGRES_URL) \
		uv run pytest tests/integration

# Run tests with coverage
coverage:
	uv run pytest --cov=sqlo --cov-report=html --cov-report=term-missing

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
	@echo "Testing Python 3.14..."
	@uv run --python 3.14 pytest || echo "Python 3.14 not available"

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
	rm -rf docs/_build

# Build documentation
docs:
	uv run sphinx-build -b html docs docs/_build/html
	@echo "Documentation built in docs/_build/html"

# Build and serve documentation
docs-serve: docs
	@echo "Serving documentation at http://localhost:8000"
	python3 -m http.server 8000 --directory docs/_build/html
