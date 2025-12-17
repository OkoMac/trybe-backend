# Code Quality Guide

This document outlines the code quality tools and practices used in the Trybe backend.

---

## 🛠️ Tools

### Code Formatting
- **Black**: Opinionated Python code formatter (line length: 100)
- **isort**: Import statement organizer

### Linting
- **flake8**: Style guide enforcement
- **pylint**: Code analysis and quality checker

### Type Checking
- **mypy**: Static type checker for Python

### Security
- **bandit**: Security vulnerability scanner

### Testing
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support

### Pre-commit Hooks
- **pre-commit**: Automated code quality checks before commits

---

## 🚀 Quick Start

### 1. Install Development Dependencies

```bash
# Local installation
pip install -r requirements/dev.txt
pre-commit install

# Or use Docker
docker-compose exec backend pip install -r requirements/dev.txt
docker-compose exec backend pre-commit install
```

### 2. Format Code

```bash
# Format with Black and isort
make format

# Or in Docker
make docker-format
```

### 3. Run Linters

```bash
# Run flake8
make lint

# Or in Docker
make docker-lint
```

### 4. Type Check

```bash
# Run mypy
make type-check
```

### 5. Security Scan

```bash
# Run bandit
make security
```

### 6. Run All Quality Checks

```bash
# Format, lint, type-check, and security scan
make quality

# Or in Docker
make docker-quality
```

---

## 📝 Pre-commit Hooks

Pre-commit hooks automatically run before each commit to ensure code quality.

### Setup

```bash
pre-commit install
```

### What Gets Checked

- Trailing whitespace
- End of file fixing
- YAML/JSON/TOML validation
- Large file detection
- Private key detection
- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)

### Manual Run

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

### Skip Hooks

```bash
# Skip pre-commit hooks (use sparingly!)
git commit --no-verify -m "message"
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_reviews.py

# Run specific test function
pytest tests/test_reviews.py::test_create_review

# Run with verbose output
pytest -v

# Run with debugging output
pytest -vv -s
```

### Coverage Reports

```bash
# Generate HTML coverage report
make test-cov

# View coverage report
open htmlcov/index.html
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_api/
│   ├── test_auth.py
│   ├── test_reviews.py
│   └── test_opportunities.py
├── test_services/
│   ├── test_review_service.py
│   └── test_email_service.py
└── test_repositories/
    └── test_review_repository.py
```

---

## 📋 Code Style Guidelines

### Formatting

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **String quotes**: Double quotes preferred
- **Imports**: Organized with isort (stdlib, third-party, first-party, local)

### Type Hints

```python
# Good - with type hints
def create_review(
    reviewer_id: uuid.UUID,
    rating: int,
    comment: str
) -> Review:
    ...

# Acceptable - complex return type
from typing import Tuple, Optional

def validate_review(
    review_id: uuid.UUID
) -> Tuple[bool, Optional[str]]:
    ...
```

### Docstrings

```python
def create_review(reviewer_id: uuid.UUID, review_data: ReviewCreate) -> Review:
    """
    Create a new review

    Args:
        reviewer_id: UUID of the reviewer
        review_data: Review data from request

    Returns:
        Created review object

    Raises:
        ValueError: If review already exists
    """
    ...
```

### Async/Await

```python
# Good - async repository methods
async def get_review(self, review_id: uuid.UUID) -> Optional[Review]:
    result = await self.db.execute(query)
    return result.scalar_one_or_none()
```

---

## 🔒 Security Best Practices

### 1. Input Validation

```python
# Use Pydantic for validation
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=10, max_length=5000)
```

### 2. SQL Injection Prevention

```python
# Good - parameterized queries
query = select(Review).where(Review.id == review_id)

# Bad - string concatenation
query = f"SELECT * FROM reviews WHERE id = '{review_id}'"  # DON'T DO THIS!
```

### 3. Authentication

```python
# Always use current_user dependency
@router.post("/reviews")
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user)
):
    ...
```

### 4. Secrets Management

```python
# Good - use environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

# Bad - hardcoded secrets
STRIPE_SECRET_KEY = "sk_test_..."  # DON'T DO THIS!
```

---

## 📊 Code Metrics

### Complexity Analysis

```bash
# Calculate cyclomatic complexity
radon cc app/ -a -nb

# Show maintainability index
radon mi app/ -nb
```

### Dead Code Detection

```bash
# Find unused code
vulture app/
```

---

## 🐛 Debugging

### Local Development

```python
# Use breakpoint() for debugging
def create_review(...):
    breakpoint()  # Drops into debugger
    ...
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

def create_review(...):
    logger.info(f"Creating review for {reviewer_id}")
    logger.debug(f"Review data: {review_data}")
    logger.error(f"Failed to create review: {error}")
```

---

## 📚 Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [bandit Documentation](https://bandit.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)

---

## ✅ Checklist Before Committing

- [ ] Code formatted with Black and isort
- [ ] No linting errors (flake8)
- [ ] Type hints added where appropriate
- [ ] Tests written for new features
- [ ] All tests passing
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] Pre-commit hooks passing

---

*Last updated: December 16, 2025*
