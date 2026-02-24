# Render Deployment Guide for TAE

## Prerequisites

1. **Render Account**: Sign up at https://render.com
2. **GitHub Repository**: TAE code pushed to GitHub
3. **External Services**: Access to CEE and ISL services

---

## Quick Start

### 1. Create PostgreSQL Database

1. Go to Render Dashboard
2. Click **New** → **PostgreSQL**
3. Configure:
   - **Name**: `tae-db`
   - **Database**: `tae_db`
   - **User**: `tae_user`
   - **Region**: Choose closest to your users
   - **Plan**: Starter ($7/mo) or Standard ($20/mo)
4. Click **Create Database**
5. **Save the Internal Database URL** (starts with `postgres://`)

### 2. Create Redis Instance

1. Click **New** → **Redis**
2. Configure:
   - **Name**: `tae-cache`
   - **Region**: Same as database
   - **Plan**: Starter ($7/mo)
   - **Maxmemory Policy**: `allkeys-lru` (for caching)
3. Click **Create Redis**
4. **Save the Internal Redis URL** (starts with `redis://`)

### 3. Create Web Service

1. Click **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `team-alignment-engine`
   - **Region**: Same as database
   - **Branch**: `main` (or your production branch)
   - **Runtime**: Python 3
   - **Build Command**: `pip install poetry && poetry install --no-dev`
   - **Start Command**: `poetry run uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Starter ($7/mo) or Standard ($25/mo)

---

## Environment Variables Configuration

### Required Environment Variables

In Render Dashboard → Environment tab, add these variables:

#### Core Application
```bash
# Environment
ENVIRONMENT=production
SERVICE_NAME=team-alignment-engine
SERVICE_VERSION=2.0.0
LOG_LEVEL=INFO

# Database (use Internal Database URL from step 1)
DATABASE_URL=<YOUR_POSTGRES_INTERNAL_URL>
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis (use Internal Redis URL from step 2)
REDIS_URL=<YOUR_REDIS_INTERNAL_URL>
REDIS_POOL_SIZE=10
REDIS_CACHE_TTL=3600
```

#### Security (Generate these securely!)
```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=<GENERATE_A_SECURE_RANDOM_STRING>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

#### External Services
```bash
# CEE Integration
CEE_BASE_URL=https://cee-service.olumi.com
CEE_API_KEY=<YOUR_CEE_API_KEY>
CEE_TIMEOUT=30
CEE_USE_MOCK=false

# ISL Integration
ISL_BASE_URL=https://isl-service.olumi.com
ISL_API_KEY=<YOUR_ISL_API_KEY>
ISL_TIMEOUT=60
```

#### PLoT Integration
```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
PLOT_INTERNAL_API_KEY=<GENERATE_A_SECURE_RANDOM_STRING>
PLOT_DEPLOYMENT_MODE=true
PLOT_ORCHESTRATION_TIMEOUT=10
PLOT_CAPABILITY_FILTERING=true
```

#### CORS Configuration
```bash
# Replace with your actual frontend URL
CORS_ORIGINS=https://your-plot-frontend.onrender.com,https://your-custom-domain.com
```

#### Phase D Features
```bash
FEATURE_PORTFOLIO_ANALYTICS_ENABLED=true
FEATURE_REALTIME_COLLABORATION_ENABLED=false
FEATURE_DECISION_DEPENDENCIES_ENABLED=true
FEATURE_ORGANIZATIONAL_PATTERNS_ENABLED=true
FEATURE_ADVANCED_ANALYTICS_ENABLED=true
FEATURE_CROSS_TEAM_COORDINATION_ENABLED=true
```

---

## Database Migration

### Initial Setup

Render will automatically run migrations on deploy if you add a **Build Command**:

```bash
pip install poetry && poetry install --no-dev && poetry run alembic upgrade head
```

### Manual Migration (if needed)

1. Connect to your Render PostgreSQL via **Shell** tab:
```bash
psql $DATABASE_URL
```

2. Run the performance indexes migration:
```bash
psql $DATABASE_URL < alembic/versions/001_add_performance_indexes.sql
```

---

## Health Check Configuration

Render automatically monitors your service health. Configure:

1. Go to **Settings** → **Health Check Path**
2. Set to: `/health`
3. Render will ping this endpoint every 30 seconds
4. If it fails 3 times, Render will restart your service

---

## Secrets Management

### Render's Built-in Secret Encryption

Render automatically encrypts all environment variables:
- ✅ **Encrypted at rest** in Render's database
- ✅ **Encrypted in transit** (TLS)
- ✅ **Only decrypted** in your running service
- ✅ **Not logged** in build logs or deployment logs

### Secret Files (for certificates, .env files)

If you need to deploy secret files:

1. Go to **Environment** → **Secret Files**
2. Click **Add Secret File**
3. Filename: `.env.production` (or your cert file)
4. Content: Paste your secret content
5. The file will be mounted at `/etc/secrets/` in your service

---

## Scaling on Render

### Horizontal Scaling (Multiple Instances)

**Good news**: Your Redis rate limiter supports horizontal scaling!

1. Go to **Settings** → **Scaling**
2. Increase **Instance Count** to 2+ instances
3. Render will load balance traffic automatically
4. Redis ensures rate limiting works across all instances

### Auto-Scaling

On Render Standard plans and above:

1. **Settings** → **Scaling** → **Auto-Scaling**
2. Set min/max instances
3. Render scales based on:
   - CPU usage
   - Memory usage
   - Request queue depth

---

## Monitoring & Alerts

### Built-in Metrics

Render provides:
- CPU usage
- Memory usage
- Request latency (p50, p95, p99)
- Error rates
- Traffic volume

### Custom Metrics (Prometheus)

TAE exposes Prometheus metrics at `/metrics`:

1. Set up external Prometheus scraper (Grafana Cloud, etc.)
2. Scrape `https://your-tae-service.onrender.com/metrics`
3. Alert on custom TAE metrics

### Log Aggregation

Forward logs to external service:

1. **Settings** → **Log Streams**
2. Add destination (Datadog, Logtail, Papertrail, etc.)
3. TAE's structured JSON logs work great with these services

---

## Custom Domain

### Add Your Domain

1. Go to **Settings** → **Custom Domain**
2. Add your domain: `tae.yourdomain.com`
3. Update DNS with Render's provided values:
   ```
   CNAME tae.yourdomain.com -> your-service.onrender.com
   ```
4. Render automatically provisions SSL certificate (Let's Encrypt)

### Update CORS

Don't forget to update `CORS_ORIGINS` environment variable with your custom domain!

---

## Zero-Downtime Deployments

Render automatically does zero-downtime deployments:

1. **Push to GitHub** → Automatic deploy triggered
2. **Render builds** new version in background
3. **Health check** validates new version
4. **Traffic switches** when new version is healthy
5. **Old version** kept running until switch completes

---

## Troubleshooting

### Database Connection Issues

Check your DATABASE_URL:
```bash
# In Render Shell
echo $DATABASE_URL

# Should be: postgresql://tae_user:password@postgres.render.internal:5432/tae_db
```

### Redis Connection Issues

Check your REDIS_URL:
```bash
# In Render Shell
echo $REDIS_URL

# Should be: redis://redis.render.internal:6379/0
```

### Startup Failures

Check logs for missing secrets:
```
ERROR: Missing required secrets: JWT_SECRET, CEE_API_KEY
Configure these in Render Dashboard > Environment
```

### Rate Limiting Not Working

Verify Redis is connected:
```bash
curl https://your-service.onrender.com/health

# Should show: "redis": {"status": "connected", "type": "redis"}
```

---

## Cost Estimate

Minimum production setup on Render:

| Service | Plan | Cost |
|---------|------|------|
| Web Service | Starter | $7/mo |
| PostgreSQL | Starter | $7/mo |
| Redis | Starter | $7/mo |
| **Total** | | **$21/mo** |

For production with auto-scaling and backups:

| Service | Plan | Cost |
|---------|------|------|
| Web Service | Standard (2 instances) | $50/mo |
| PostgreSQL | Standard (daily backups) | $20/mo |
| Redis | Standard | $15/mo |
| **Total** | | **$85/mo** |

---

## Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] Database migrations run
- [ ] Performance indexes applied
- [ ] Health check returns `200 OK`
- [ ] Secrets validated (no startup errors)
- [ ] CORS configured with actual domains
- [ ] Custom domain configured (optional)
- [ ] Monitoring/alerts set up
- [ ] Load testing completed
- [ ] Rate limiting tested
- [ ] Backup strategy in place

---

## Support

- **Render Documentation**: https://render.com/docs
- **Render Status**: https://status.render.com
- **TAE Issues**: https://github.com/Talchain/Team-Alignment-Engine/issues

---

**Last Updated**: 2025-11-22
**TAE Version**: 2.0.0
