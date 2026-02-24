# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 14+ (if not using Docker)
- Redis 7+ (if not using Docker)
- Access to CEE and ISL services

## Environment Configuration

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Configure required variables:

```bash
# Service
SERVICE_NAME=team-alignment-engine
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/tae_db

# Redis
REDIS_URL=redis://host:6379/0

# CEE Integration
CEE_BASE_URL=https://cee-service.olumi.com
CEE_API_KEY=your_cee_api_key

# ISL Integration
ISL_BASE_URL=https://isl-service.olumi.com
ISL_API_KEY=your_isl_api_key

# Security
JWT_SECRET=your_secure_secret_here
```

## Docker Deployment

### Development

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f tae

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -t team-alignment-engine:1.0.0 .

# Run with production settings
docker run -d \
  --name tae \
  -p 8000:8000 \
  -p 9090:9090 \
  --env-file .env \
  team-alignment-engine:1.0.0
```

## Kubernetes Deployment

Apply manifests:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

## Database Migrations

Run Alembic migrations:

```bash
# Generate migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one version
poetry run alembic downgrade -1
```

## Monitoring

### Health Checks

- **Endpoint:** `GET /health`
- **Interval:** 30s
- **Timeout:** 3s

### Prometheus Metrics

- **Endpoint:** `http://localhost:9090/metrics`
- **Metrics:**
  - `tae_sessions_created_total`
  - `tae_validations_requested_total`
  - `tae_request_duration_seconds`

### Logging

Structured JSON logs to stdout:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "name": "tae.service",
  "message": "Session created",
  "session_id": "..."
}
```

## Scaling

### Horizontal Scaling

Service is stateless and can be scaled horizontally:

```bash
# Docker Compose
docker-compose up -d --scale tae=3

# Kubernetes
kubectl scale deployment tae --replicas=3
```

### Database Connection Pooling

Configure in `.env`:

```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Redis Caching

Configure TTL:

```bash
REDIS_CACHE_TTL=3600  # 1 hour
```

## Security

### TLS/HTTPS

Use reverse proxy (nginx, Traefik) for TLS termination.

### Secrets Management

Use secrets manager (Vault, AWS Secrets Manager):

```bash
# Example with Kubernetes secrets
kubectl create secret generic tae-secrets \
  --from-literal=cee-api-key=$CEE_API_KEY \
  --from-literal=isl-api-key=$ISL_API_KEY \
  --from-literal=jwt-secret=$JWT_SECRET
```

## Troubleshooting

### Connection Issues

```bash
# Check database connectivity
docker-compose exec tae psql $DATABASE_URL

# Check Redis connectivity
docker-compose exec tae redis-cli -u $REDIS_URL ping
```

### Performance Issues

```bash
# Check resource usage
docker stats tae

# Check logs for errors
docker-compose logs --tail=100 tae
```

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG docker-compose up
```
