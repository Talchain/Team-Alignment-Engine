# Developer Getting Started Guide

**Team Alignment Engine - Phase D Development Setup**

Version: 2.0.0
Last Updated: 2025-01-31

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Running the Application](#running-the-application)
5. [Testing](#testing)
6. [Development Workflow](#development-workflow)
7. [Debugging](#debugging)
8. [Common Issues](#common-issues)

---

## Prerequisites

### Required Software

- **Python 3.11+**: TAE Phase D requires Python 3.11 or higher
- **PostgreSQL 15+**: Primary database
- **Redis 7.0+**: Caching and WebSocket pub/sub
- **Docker & Docker Compose** (optional): For containerized development
- **Git**: Version control

### Recommended IDE Setup

- **VS Code** with extensions:
  - Python (Microsoft)
  - Pylance
  - Python Test Explorer
  - Docker
  - PostgreSQL (Chris Kolkman)
- **PyCharm Professional**: Built-in database tools and Python support

---

## Environment Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/olumi/Team-Alignment-Engine.git
cd Team-Alignment-Engine
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.11+
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
pip list | grep fastapi
pip list | grep sqlalchemy
```

**Key Dependencies**:
```
fastapi==0.104.1
sqlalchemy==2.0.23
pydantic==2.5.0
redis[hiredis]==5.0.1
networkx==3.2
asyncpg==0.29.0
```

### Step 4: Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Minimal `.env` for Development**:
```bash
# Service Configuration
SERVICE_NAME=team-alignment-engine
SERVICE_VERSION=2.0.0
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgresql://tae_dev:dev_password@localhost:5432/tae_development
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# Phase D: CEE Integration (use mock for development)
CEE_USE_MOCK=true
CEE_BASE_URL=http://localhost:8001
CEE_API_KEY=dev_key_not_used_in_mock_mode

# Phase D: WebSocket Configuration
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS_PER_SESSION=50

# Phase D: Feature Flags (all enabled for development)
FEATURE_PORTFOLIO_ANALYTICS_ENABLED=true
FEATURE_REALTIME_COLLABORATION_ENABLED=true
FEATURE_DECISION_DEPENDENCIES_ENABLED=true
FEATURE_ORGANIZATIONAL_PATTERNS_ENABLED=true
FEATURE_ADVANCED_ANALYTICS_ENABLED=true
FEATURE_CROSS_TEAM_COORDINATION_ENABLED=true

# Logging
LOG_LEVEL=DEBUG
```

---

## Database Setup

### Option 1: Local PostgreSQL

**Install PostgreSQL**:

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15
sudo systemctl start postgresql

# Verify installation
psql --version
```

**Create Database and User**:

```bash
# Connect to PostgreSQL
psql postgres

# Create user and database
CREATE USER tae_dev WITH PASSWORD 'dev_password';
CREATE DATABASE tae_development OWNER tae_dev;
GRANT ALL PRIVILEGES ON DATABASE tae_development TO tae_dev;
\q
```

**Install Redis**:

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Verify
redis-cli ping  # Should return PONG
```

### Option 2: Docker Compose (Recommended)

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: tae_dev
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: tae_development
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

```bash
# Start services
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Check logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Run Database Migrations

```bash
# Verify current migration status
alembic current

# Run all migrations
alembic upgrade head

# Verify migration completed
alembic current  # Should show latest migration (003)

# Check tables created
psql -h localhost -U tae_dev -d tae_development -c "\dt"
```

**Expected Tables (Phase D)**:
- `sessions`, `options`, `votes`, `concerns`, `perspectives` (Phases A-B)
- `decision_dependencies` (D3)
- `coordination_groups`, `coordination_group_sessions`, `coordination_conflicts`, `conflict_sessions` (D6)

### Seed Development Data (Optional)

```bash
# Load sample data for testing
python -m scripts.seed_dev_data

# This creates:
# - 2 organizations
# - 10 sample sessions with varying statuses
# - Dependencies between sessions
# - Coordination groups
```

---

## Running the Application

### Development Server

```bash
# Run with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# With debug logging
LOG_LEVEL=DEBUG uvicorn src.main:app --reload --port 8000

# With multiple workers (production-like)
uvicorn src.main:app --workers 4 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Verify Application Running

```bash
# Health check
curl http://localhost:8000/health | jq

# Expected response:
# {
#   "status": "ok",
#   "service": "team-alignment-engine",
#   "version": "2.0.0",
#   "environment": "development",
#   "dependencies": {
#     "database": {"status": "connected"},
#     "redis": {"status": "connected"}
#   },
#   "phase_d_capabilities": {
#     "d1_portfolio_analytics": true,
#     "d2_realtime_collaboration": true,
#     ...
#   }
# }
```

### Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

---

## Testing

### Run All Tests

```bash
# Run entire test suite
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Run Phase D Tests Only

```bash
# Run all Phase D tests
pytest tests/test_phase_d_*.py -v

# Run specific capability tests
pytest tests/test_phase_d_portfolio.py -v
pytest tests/test_phase_d_collaboration.py -v
pytest tests/test_phase_d_dependencies.py -v
pytest tests/test_phase_d_patterns.py -v
pytest tests/test_phase_d_analytics.py -v
pytest tests/test_phase_d_coordination.py -v
```

### Run Integration Tests

```bash
# Requires database and Redis running
pytest tests/integration/ -v

# Skip slow tests
pytest -m "not slow"

# Run only WebSocket tests
pytest tests/integration/test_websocket.py -v
```

### Run Load Tests (k6)

```bash
# Install k6 (macOS)
brew install k6

# Run pilot load test (15-40 users)
k6 run tests/load/pilot_load_test.js

# Run stress test
k6 run --vus 100 --duration 5m tests/load/stress_test.js
```

### Test Specific Endpoints

```bash
# Test portfolio analytics
curl -X GET "http://localhost:8000/api/v1/portfolio/analytics?organization_id=550e8400-e29b-41d4-a716-446655440000&start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z" | jq

# Test dependency graph
curl -X GET "http://localhost:8000/api/v1/dependencies/graph?organization_id=550e8400-e29b-41d4-a716-446655440000" | jq

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/collaboration/ws/550e8400-e29b-41d4-a716-446655440000?user_id=alice"
```

---

## Development Workflow

### Typical Development Cycle

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make Changes**
   - Edit code in `src/`
   - Add tests in `tests/`
   - Update documentation if needed

3. **Run Tests**
   ```bash
   pytest tests/test_my_feature.py -v
   ```

4. **Format Code**
   ```bash
   # Format with black
   black src/ tests/

   # Sort imports
   isort src/ tests/

   # Lint with flake8
   flake8 src/ tests/
   ```

5. **Type Check**
   ```bash
   mypy src/
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(phase-d): add new analytics capability"
   ```

7. **Push and Create PR**
   ```bash
   git push origin feature/my-new-feature
   # Create pull request on GitHub
   ```

### Code Style Guidelines

**Black Formatting**:
```bash
# Format all Python files
black --line-length 100 src/ tests/

# Check without modifying
black --check src/
```

**Import Sorting**:
```bash
# Sort imports
isort --profile black src/ tests/

# Check without modifying
isort --check src/
```

**Type Hints**:
```python
# Always use type hints for function signatures
async def get_portfolio_analytics(
    organization_id: UUID,
    filters: PortfolioFilters,
    db: AsyncSession
) -> PortfolioAnalysis:
    ...
```

**Docstrings** (Google style):
```python
def analyze_trends(metric_name: str, lookback_days: int) -> TrendAnalysis:
    """Analyze trends for a decision metric.

    Args:
        metric_name: Name of metric to analyze (e.g., "decision_time")
        lookback_days: Number of days of history to analyze

    Returns:
        TrendAnalysis object with trend line, forecast, and changepoints

    Raises:
        ValueError: If metric_name is invalid or lookback_days < 30
    """
    ...
```

---

## Debugging

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG

# Or via environment variable
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### VS Code Debugger Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Python: Current Test File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "-s"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### Debug WebSocket Connections

```bash
# Enable WebSocket debug logging
export LOG_LEVEL=DEBUG

# Use browser dev tools (Chrome/Firefox)
# Open Console tab
# Run:
const ws = new WebSocket('ws://localhost:8000/api/v1/collaboration/ws/session-id?user_id=test');
ws.onmessage = (event) => console.log('Received:', event.data);
ws.send(JSON.stringify({type: 'heartbeat', timestamp: new Date().toISOString()}));
```

### Database Query Debugging

```bash
# Enable SQL logging in .env
DATABASE_ECHO=true

# Or in code
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, echo=True)

# View slow queries in PostgreSQL logs
tail -f /var/log/postgresql/postgresql-15-main.log | grep "duration:"
```

### Redis Debugging

```bash
# Monitor Redis commands
redis-cli MONITOR

# Check keys
redis-cli KEYS "session:*"

# Inspect key value
redis-cli GET "portfolio:org-id:start:end"

# Check TTL
redis-cli TTL "portfolio:org-id:start:end"
```

---

## Common Issues

### Issue 1: Database Connection Refused

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
echo $DATABASE_URL

# Verify port is correct (default: 5432)
psql -h localhost -U tae_dev -d tae_development

# If using Docker, check container status
docker-compose -f docker-compose.dev.yml ps
```

### Issue 2: Redis Connection Failed

**Error**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solutions**:
```bash
# Check Redis is running
redis-cli ping

# Verify Redis URL in .env
echo $REDIS_URL

# Check port (default: 6379)
redis-cli -h localhost -p 6379 ping
```

### Issue 3: Migration Fails

**Error**: `alembic.util.exc.CommandError: Can't locate revision identified by '...'`

**Solutions**:
```bash
# Check current migration
alembic current

# View migration history
alembic history

# If out of sync, reset to head
alembic stamp head

# Rerun migrations
alembic upgrade head

# If still failing, drop database and recreate
dropdb -h localhost -U tae_dev tae_development
createdb -h localhost -U tae_dev tae_development
alembic upgrade head
```

### Issue 4: Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solutions**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
python -m src.main
```

### Issue 5: WebSocket Connection Drops

**Error**: WebSocket closes unexpectedly

**Solutions**:
```bash
# Check heartbeat interval in .env
echo $WEBSOCKET_HEARTBEAT_INTERVAL  # Should be 30

# Increase idle timeout
export WEBSOCKET_IDLE_TIMEOUT=600  # 10 minutes

# Check Redis pub/sub working
redis-cli SUBSCRIBE test_channel
# In another terminal:
redis-cli PUBLISH test_channel "hello"

# Enable debug logging
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Issue 6: Tests Fail with "Database already exists"

**Error**: `ProgrammingError: database "tae_test" already exists`

**Solutions**:
```bash
# Drop test database
dropdb -h localhost -U tae_dev tae_test

# Rerun tests
pytest

# Or configure pytest to use unique test database
# In conftest.py, use unique database name per test session
```

---

## Next Steps

- Review [Phase D Architecture Documentation](../architecture/phase-d-overview.md)
- Read [API Documentation](../api/phase-d-openapi.yml)
- Check [Contributing Guidelines](../../CONTRIBUTING.md)
- Join #tae-dev Slack channel for questions

---

## Helpful Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)
- [Redis Python Client](https://redis-py.readthedocs.io/)

---

**Document Maintained By**: Platform Engineering Team
**Last Review Date**: 2025-01-31
**Next Review Date**: 2025-04-30
