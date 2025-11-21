#!/bin/bash
# Development helper scripts

set -e

case "$1" in
  install)
    echo "Installing dependencies..."
    poetry install
    ;;

  db:setup)
    echo "Setting up database..."
    poetry run alembic upgrade head
    ;;

  db:reset)
    echo "Resetting database..."
    poetry run alembic downgrade base
    poetry run alembic upgrade head
    ;;

  test)
    echo "Running tests..."
    poetry run pytest "${@:2}"
    ;;

  test:unit)
    echo "Running unit tests..."
    poetry run pytest tests/unit/ -v
    ;;

  test:integration)
    echo "Running integration tests..."
    poetry run pytest tests/integration/ -v
    ;;

  test:e2e)
    echo "Running E2E tests..."
    poetry run pytest tests/e2e/ -v
    ;;

  test:coverage)
    echo "Running tests with coverage..."
    poetry run pytest --cov=src --cov-report=html --cov-report=term
    echo "Coverage report generated in htmlcov/index.html"
    ;;

  format)
    echo "Formatting code..."
    poetry run black src/ tests/
    ;;

  lint)
    echo "Linting code..."
    poetry run ruff src/ tests/
    ;;

  typecheck)
    echo "Type checking..."
    poetry run mypy src/
    ;;

  dev)
    echo "Starting development server..."
    poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
    ;;

  docker:build)
    echo "Building Docker image..."
    docker build -t team-alignment-engine:latest .
    ;;

  docker:up)
    echo "Starting Docker services..."
    docker-compose up -d
    ;;

  docker:down)
    echo "Stopping Docker services..."
    docker-compose down
    ;;

  docker:logs)
    echo "Viewing Docker logs..."
    docker-compose logs -f tae
    ;;

  clean)
    echo "Cleaning up..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    echo "Cleanup complete"
    ;;

  *)
    echo "Team Alignment Engine - Development Scripts"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install          - Install dependencies"
    echo "  db:setup         - Setup database with migrations"
    echo "  db:reset         - Reset database"
    echo "  test             - Run all tests"
    echo "  test:unit        - Run unit tests"
    echo "  test:integration - Run integration tests"
    echo "  test:e2e         - Run E2E tests"
    echo "  test:coverage    - Run tests with coverage report"
    echo "  format           - Format code with Black"
    echo "  lint             - Lint code with Ruff"
    echo "  typecheck        - Type check with MyPy"
    echo "  dev              - Start development server"
    echo "  docker:build     - Build Docker image"
    echo "  docker:up        - Start Docker services"
    echo "  docker:down      - Stop Docker services"
    echo "  docker:logs      - View Docker logs"
    echo "  clean            - Clean up cache files"
    ;;
esac
