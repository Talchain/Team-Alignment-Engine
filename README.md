# Team Alignment Engine (TAE)

**Version:** 1.0.0
**Status:** Production Ready

## Mission Statement

Build a causally-validated team deliberation system that prevents product teams from aligning on options with weak assumptions. TAE structures messy stakeholder perspectives, surfaces disagreement axes, validates all options with ISL's causal analysis, and protects evidence-based minority concerns.

**Core Value:** Teams see causal reality DURING deliberation, not just after consensus.

## Architecture

```
UI → PLoT Engine (orchestrator)
         ↓
         ├→ CEE (language understanding)
         ├→ ISL (causal validation)
         └→ TAE (deliberation orchestration)
```

## Features

### Phase A: Structured Deliberation
- ✅ Session management with stakeholder roles
- ✅ Structured perspective collection via CEE
- ✅ Goal profile extraction (8 dimensions)
- ✅ Shared ground identification
- ✅ Disagreement mapping
- ✅ Option fit calculation
- ✅ Decision type templates

### Phase B: Causal Validation
- ✅ Parallel ISL validation for all options
- ✅ Baseline "Status Quo" comparison
- ✅ Evidence-based minority protection
- ✅ Sensitivity analysis on contested assumptions
- ✅ Complete decision audit trail
- ✅ Scenario model integration

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Access to CEE and ISL services

### Installation

```bash
# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the service
poetry run uvicorn src.api.main:app --reload
```

### Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test suite
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/

# Check coverage
poetry run pytest --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run ruff src/ tests/

# Type check
poetry run mypy src/
```

## API Documentation

Once running, visit:
- **Interactive docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

## Project Structure

```
tae-service/
├── src/
│   ├── api/           # FastAPI routes and middleware
│   ├── services/      # Business logic services
│   ├── models/        # Pydantic data models
│   ├── clients/       # External service clients (CEE, ISL)
│   ├── storage/       # Database and cache
│   └── config/        # Configuration
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests
├── docs/              # Documentation
├── alembic/           # Database migrations
└── docker/            # Docker configuration
```

## Configuration

Key environment variables:

```bash
# Service
SERVICE_NAME=team-alignment-engine
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:pass@host:5432/tae

# Redis
REDIS_URL=redis://host:6379/0

# CEE Integration
CEE_BASE_URL=https://cee-service.olumi.com
CEE_API_KEY=<secret>

# ISL Integration
ISL_BASE_URL=https://isl-service.olumi.com
ISL_API_KEY=<secret>
```

## Monitoring

- **Prometheus metrics:** http://localhost:9090/metrics
- **Health endpoint:** http://localhost:8000/health
- **Structured JSON logging** to stdout

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for:
- Docker deployment
- Kubernetes configuration
- Production best practices

## Integration

### CEE Integration
TAE calls CEE for all LLM work:
- Profile extraction from free-text
- Shared ground summarization
- Validation explanations

### ISL Integration
TAE calls ISL for causal validation:
- Option validation with outcome predictions
- Sensitivity analysis for minority concerns
- Assumption strength assessment

## License

Proprietary - Olumi Inc.

## Support

For issues or questions:
- GitHub Issues: https://github.com/Talchain/Team-Alignment-Engine/issues
- Email: support@olumi.com
