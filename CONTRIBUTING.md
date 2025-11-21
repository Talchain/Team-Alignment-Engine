# Contributing to Team Alignment Engine

Thank you for your interest in contributing to the Team Alignment Engine!

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry 1.7+
- PostgreSQL 14+
- Redis 7+
- Docker (optional)

### Quick Start

```bash
# Clone repository
git clone https://github.com/Talchain/Team-Alignment-Engine.git
cd Team-Alignment-Engine

# Install dependencies
./scripts/dev.sh install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start services with Docker
./scripts/dev.sh docker:up

# Or manually:
# Start PostgreSQL and Redis
# Run database migrations
./scripts/dev.sh db:setup

# Start development server
./scripts/dev.sh dev
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow these guidelines:

- **Code Style:** Use Black for formatting
- **Linting:** Use Ruff for linting
- **Type Hints:** Add type hints to all functions
- **Docstrings:** Document all public functions
- **Tests:** Write tests for new features

### 3. Run Tests

```bash
# Run all tests
./scripts/dev.sh test

# Run specific test suite
./scripts/dev.sh test:unit
./scripts/dev.sh test:integration
./scripts/dev.sh test:e2e

# Check coverage
./scripts/dev.sh test:coverage
```

### 4. Format and Lint

```bash
# Format code
./scripts/dev.sh format

# Lint code
./scripts/dev.sh lint

# Type check
./scripts/dev.sh typecheck
```

### 5. Commit Changes

Follow conventional commit format:

```bash
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug in validation"
git commit -m "docs: update API documentation"
git commit -m "test: add tests for concern validator"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable
- Test results

## Code Standards

### Python Style

- **Line Length:** 100 characters (configured in pyproject.toml)
- **Imports:** Grouped and sorted (stdlib, third-party, local)
- **Naming:**
  - Classes: `PascalCase`
  - Functions/Variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`

### Error Handling

Always use error.v1 standard for API errors:

```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Clear error message"
)
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "Operation completed",
    extra={
        "session_id": session_id,
        "duration_ms": duration,
    }
)
```

### Testing

#### Unit Tests

Test individual functions/methods:

```python
@pytest.mark.asyncio
async def test_function_name():
    """Test what the function does."""
    # Arrange
    input_data = create_test_data()

    # Act
    result = await function_under_test(input_data)

    # Assert
    assert result.expected_field == expected_value
```

#### Integration Tests

Test API endpoints:

```python
@pytest.mark.asyncio
async def test_endpoint_name(client: AsyncClient):
    """Test endpoint behavior."""
    response = await client.post("/endpoint", json=data)

    assert response.status_code == 201
    assert "field" in response.json()
```

#### E2E Tests

Test complete workflows:

```python
@pytest.mark.asyncio
async def test_complete_workflow():
    """Test full user journey."""
    # Create session -> Collect perspectives -> Propose options -> Decide
    pass
```

## Project Structure

```
tae-service/
├── src/
│   ├── api/           # FastAPI routes and middleware
│   ├── services/      # Business logic
│   ├── models/        # Pydantic data models
│   ├── clients/       # External service clients
│   ├── storage/       # Database and cache
│   └── config/        # Configuration
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   ├── e2e/           # End-to-end tests
│   └── fixtures/      # Test fixtures and mocks
├── docs/              # Documentation
├── scripts/           # Development scripts
└── alembic/           # Database migrations
```

## Adding New Features

### 1. Data Models

Define Pydantic models in `src/models/`:

```python
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class MyModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=200)
    value: float = Field(..., ge=0, le=1)
```

### 2. Services

Implement business logic in `src/services/`:

```python
class MyService:
    """Service for managing X."""

    async def create(self, data: MyModel) -> MyModel:
        """Create new X."""
        # Implementation
        pass
```

### 3. API Endpoints

Add routes in `src/api/routes/`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/my-resource", tags=["my-resource"])

@router.post("")
async def create_resource(request: CreateRequest):
    """Create new resource."""
    # Implementation
    pass
```

### 4. Tests

Add tests in `tests/`:

```python
# tests/unit/test_my_service.py
@pytest.mark.asyncio
async def test_my_service_create():
    """Test service creation."""
    pass

# tests/integration/test_my_endpoints.py
@pytest.mark.asyncio
async def test_create_resource(client):
    """Test resource creation endpoint."""
    pass
```

### 5. Database Migrations

If adding/changing database schema:

```bash
# Generate migration
poetry run alembic revision --autogenerate -m "Add my_table"

# Review and edit migration file
vim alembic/versions/xxx_add_my_table.py

# Apply migration
poetry run alembic upgrade head
```

## Debug Tips

### Running with Debug Logs

```bash
LOG_LEVEL=DEBUG ./scripts/dev.sh dev
```

### Using Python Debugger

Add breakpoint in code:

```python
import pdb; pdb.set_trace()
```

### Inspecting Database

```bash
# Connect to database
psql $DATABASE_URL

# View sessions
SELECT * FROM sessions LIMIT 10;
```

### Checking Redis

```bash
# Connect to Redis
redis-cli -u $REDIS_URL

# View keys
KEYS *
```

## Performance Considerations

- **Database Queries:** Use indexes, avoid N+1 queries
- **Caching:** Cache expensive computations
- **Async/Await:** Use async for I/O operations
- **Pagination:** Paginate large result sets

## Security Guidelines

- **Input Validation:** Validate all inputs with Pydantic
- **Authentication:** Require auth on sensitive endpoints
- **Rate Limiting:** Enforce rate limits
- **SQL Injection:** Use parameterized queries (use SQLAlchemy, never string formatting)
- **XSS:** Sanitize user input
- **Secrets:** Never commit secrets to git
- **WebSocket Authentication:** Validate user_id before establishing connection
- **Dependency Validation:** Prevent circular dependencies before insertion

## Phase D-Specific Guidelines

### D1: Portfolio Analytics

- Always cache results with appropriate TTL (5-10 minutes)
- Use async database queries with connection pooling
- Implement pagination for large result sets
- Document performance targets in tests

### D2: Real-Time Collaboration

- Test WebSocket connections with heartbeat mechanism
- Handle connection drops gracefully
- Use Redis pub/sub for broadcasting (not database polling)
- Monitor connection limits per session (default: 50)

### D3: Decision Dependencies

- Always check for circular dependencies before insertion
- Cache dependency graphs (TTL: 5 minutes)
- Use NetworkX for graph algorithms
- Test with complex dependency chains (>10 nodes)

### D4: Organizational Patterns

- Require minimum sample size (default: 3 sessions per pattern)
- Cache pattern analysis results (TTL: 1 hour)
- Document pattern classification thresholds
- Include confidence scores in results

### D5: Advanced Analytics

- Use scipy/numpy for statistical calculations
- Document statistical methods in docstrings
- Include confidence intervals in forecasts
- Cache analytics results (TTL: 1-4 hours based on data volatility)

### D6: Cross-Team Coordination

- Test all four conflict types (temporal, resource, dependency, scope)
- Document conflict severity thresholds
- Generate actionable resolution suggestions
- Cache coordination views (TTL: 5 minutes)

## Performance Requirements

All Phase D endpoints must meet these performance targets (p95 latency):

- Portfolio Analytics (100 sessions): <5s
- Health Score: <1s
- WebSocket Broadcast: <100ms
- Dependency Graph (100 decisions): <2s
- Pattern Analysis (90 days): <3s
- Trend Analysis (90 days): <2s
- Benchmarks: <1s
- Coordination View (50 sessions): <2s

If your changes impact performance, include load test results in your PR.

## Documentation Requirements

When adding Phase D features, update:

1. **OpenAPI Spec** (`docs/api/phase-d-openapi.yml`):
   - Add endpoint definition
   - Include request/response schemas
   - Add concrete examples
   - Document error responses

2. **Architecture Documentation** (`docs/architecture/phase-d-overview.md`):
   - Update capability descriptions
   - Add architecture diagrams if needed
   - Document design decisions

3. **Developer Guide** (`docs/developers/GETTING_STARTED.md`):
   - Update setup instructions if dependencies change
   - Add testing instructions for new features

4. **Operational Runbooks** (`docs/operations/runbooks/`):
   - Add troubleshooting procedures for new features
   - Document scaling/performance tuning
   - Include disaster recovery procedures

## Getting Help

- **Documentation:** Check `/docs` directory
- **Phase D Architecture:** `docs/architecture/phase-d-overview.md`
- **API Documentation:** `docs/api/phase-d-openapi.yml`
- **Developer Guide:** `docs/developers/GETTING_STARTED.md`
- **API Docs:** Run server and visit `http://localhost:8000/docs`
- **Slack:** #tae-dev channel
- **Issues:** Search existing issues on GitHub
- **Discussions:** Ask questions in GitHub Discussions

## Code Review Checklist

Before requesting review, ensure:

- [ ] Tests added/updated and passing (`pytest`)
- [ ] Code coverage maintained (>80%)
- [ ] Performance targets met (run load tests if applicable)
- [ ] Type hints added (`mypy src/` passes)
- [ ] Code formatted (`black`, `isort`)
- [ ] Linting passes (`flake8`)
- [ ] Documentation updated
- [ ] Commit messages follow conventional format
- [ ] PR description complete with testing details

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
