.PHONY: help format lint type-check security test test-cov clean install-dev pre-commit quality all

help:
	@echo "Available commands:"
	@echo "  make format        - Format code with Black and isort"
	@echo "  make lint          - Lint code with flake8 and pylint"
	@echo "  make type-check    - Run type checking with mypy"
	@echo "  make security      - Run security scan with bandit"
	@echo "  make test          - Run tests with pytest"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make quality       - Run all quality checks"
	@echo "  make pre-commit    - Run pre-commit hooks on all files"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make clean         - Remove cache and generated files"

install-dev:
	pip install -r requirements/dev.txt
	pre-commit install

format:
	@echo "Running Black..."
	black app/ tests/
	@echo "Running isort..."
	isort app/ tests/
	@echo "✓ Code formatted successfully"

lint:
	@echo "Running flake8..."
	flake8 app/ tests/ --count --statistics
	@echo "✓ Linting passed"

type-check:
	@echo "Running mypy..."
	mypy app/
	@echo "✓ Type checking passed"

security:
	@echo "Running bandit..."
	bandit -r app/ -c pyproject.toml
	@echo "✓ Security scan passed"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "✓ Tests passed"

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "✓ Tests passed. Coverage report generated in htmlcov/"

pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files
	@echo "✓ Pre-commit checks passed"

quality: format lint type-check security
	@echo "✓ All quality checks passed!"

all: install-dev quality test
	@echo "✓ All checks passed!"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "✓ Cleanup complete"

# Docker commands
docker-format:
	docker-compose exec backend make format

docker-lint:
	docker-compose exec backend make lint

docker-test:
	docker-compose exec backend make test

docker-quality:
	docker-compose exec backend make quality
