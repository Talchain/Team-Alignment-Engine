# Team Alignment Engine

**Causally-validated team deliberation that prevents alignment on weak assumptions.**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

---

## What is TAE?

TAE structures messy stakeholder perspectives, surfaces disagreement axes, validates all options with causal analysis (ISL), and protects evidence-based minority concerns.

**Core Value:** Teams see causal reality DURING deliberation, not just after consensus.

---

## Architecture

```
┌─────────────────────────────────────────┐
│          Olumi Ecosystem                 │
├─────────────────────────────────────────┤
│                                           │
│  UI → PLoT Engine (orchestrator)         │
│           ↓                               │
│           ├→ CEE (language understanding) │
│           ├→ ISL (causal validation)      │
│           └→ TAE (deliberation)           │
│                                           │
└─────────────────────────────────────────┘
```

---

## Features

- ✅ **Structured Deliberation** - Session management, perspective collection, disagreement mapping
- ✅ **Causal Validation** - ISL integration, outcome prediction, sensitivity analysis
- ✅ **AI Assistance** - Option generation, synthesis, tuning, assumption testing, retrospectives
- ✅ **Multi-Round Deliberation** - Anonymous voting, convergence detection, Pareto analysis
- ✅ **Organizational Intelligence** - Portfolio analytics, real-time collaboration (WebSocket), decision dependencies
- ✅ **Advanced Analytics** - Trend analysis, forecasting, comparative benchmarking
- ✅ **Cross-Team Coordination** - Conflict detection, resolution suggestions
- ✅ **Autonomous Learning** - Outcome tracking, pattern learning, causal graph refinement

See [TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md) for complete phase details (A, B, C, D, 5).

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/Talchain/Team-Alignment-Engine.git
cd Team-Alignment-Engine

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your database and service URLs

# Run database migrations
poetry run alembic upgrade head

# Start the service
poetry run uvicorn src.api.main:app --reload
```

**Access the API:**
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Documentation

| Document | Purpose |
|----------|---------|
| **[GETTING_STARTED.md](./GETTING_STARTED.md)** | New developer onboarding (installation, dev workflow, testing, troubleshooting) |
| **[TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md)** | Complete technical reference (architecture, all APIs, data models, deployment) |
| **[CONTRIBUTING.md](./CONTRIBUTING.md)** | Contribution guidelines |
| **[CHANGELOG.md](./CHANGELOG.md)** | Version history |

---

## Tech Stack

- **API Framework:** FastAPI (async)
- **Database:** PostgreSQL 15+ (SQLAlchemy 2.0)
- **Caching:** Redis 7.0+
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-asyncio
- **External Services:** CEE (language), ISL (causal), FACET (robustness), LLM (AI)

---

## Project Structure

```
Team-Alignment-Engine/
├── src/
│   ├── api/          # Routes (23 files, 60+ endpoints)
│   ├── services/     # Business logic (31 services)
│   ├── models/       # Pydantic models (100+)
│   ├── storage/      # Database & repositories
│   ├── clients/      # External service clients
│   └── auth/         # JWT authentication
├── tests/            # Unit, integration, e2e
├── alembic/          # Database migrations (001-007)
├── docs/             # Additional documentation
└── .env.example      # Environment template
```

---

## License

Proprietary - Olumi Inc.

---

## Support

- **Issues:** https://github.com/Talchain/Team-Alignment-Engine/issues
- **Slack:** #tae-dev
- **Email:** platform@olumi.com
