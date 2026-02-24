"""Configuration validation command."""

import os
from typing import Dict, List
from pathlib import Path

from src.config import settings


REQUIRED_SECRETS = {
    "development": [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET",
    ],
    "staging": [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET",
        "CEE_API_KEY",
        "ISL_API_KEY",
        "PLOT_INTERNAL_API_KEY",
    ],
    "production": [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET",
        "CEE_BASE_URL",
        "CEE_API_KEY",
        "ISL_BASE_URL",
        "ISL_API_KEY",
        "PLOT_INTERNAL_API_KEY",
    ],
}


def validate_configuration(env: str) -> Dict[str, List[Dict]]:
    """
    Validate environment configuration.

    Args:
        env: Environment name (development, staging, production)

    Returns:
        Validation results by category
    """
    results = {
        "Environment Variables": _validate_env_vars(env),
        "Database Configuration": _validate_database(),
        "Redis Configuration": _validate_redis(),
        "Security Settings": _validate_security(env),
        "External Services": _validate_external_services(env),
        "Feature Flags": _validate_feature_flags(),
    }

    return results


def _validate_env_vars(env: str) -> List[Dict]:
    """Validate required environment variables."""
    checks = []

    required = REQUIRED_SECRETS.get(env, REQUIRED_SECRETS["development"])

    for var_name in required:
        value = os.getenv(var_name)
        checks.append({
            "name": var_name,
            "valid": bool(value),
            "message": "Set" if value else "Missing - required for this environment",
        })

    return checks


def _validate_database() -> List[Dict]:
    """Validate database configuration."""
    checks = []

    # Check DATABASE_URL format
    db_url = settings.database_url
    checks.append({
        "name": "DATABASE_URL format",
        "valid": db_url.startswith("postgresql"),
        "message": "Valid PostgreSQL URL" if db_url.startswith("postgresql") else "Must start with postgresql://",
    })

    # Check pool settings
    checks.append({
        "name": "Connection pool size",
        "valid": 5 <= settings.database_pool_size <= 50,
        "message": f"{settings.database_pool_size} (recommended: 10-20)",
    })

    checks.append({
        "name": "Max overflow",
        "valid": settings.database_max_overflow >= settings.database_pool_size,
        "message": f"{settings.database_max_overflow}",
    })

    return checks


def _validate_redis() -> List[Dict]:
    """Validate Redis configuration."""
    checks = []

    redis_url = settings.redis_url
    checks.append({
        "name": "REDIS_URL format",
        "valid": redis_url.startswith("redis://"),
        "message": "Valid Redis URL" if redis_url.startswith("redis://") else "Must start with redis://",
    })

    checks.append({
        "name": "Redis pool size",
        "valid": 5 <= settings.redis_pool_size <= 50,
        "message": f"{settings.redis_pool_size}",
    })

    checks.append({
        "name": "Cache TTL",
        "valid": settings.redis_cache_ttl > 0,
        "message": f"{settings.redis_cache_ttl}s",
    })

    return checks


def _validate_security(env: str) -> List[Dict]:
    """Validate security settings."""
    checks = []

    # JWT secret length
    jwt_secret = settings.jwt_secret
    checks.append({
        "name": "JWT_SECRET length",
        "valid": len(jwt_secret) >= 32,
        "message": f"{len(jwt_secret)} chars (minimum: 32)" if len(jwt_secret) >= 32 else "Too short - use 32+ characters",
    })

    # Rate limiting
    checks.append({
        "name": "Rate limiting",
        "valid": settings.rate_limit_requests > 0,
        "message": f"{settings.rate_limit_requests} requests per {settings.rate_limit_window}s",
    })

    # CORS configuration
    cors_origins = settings.get_cors_origins()
    if env == "production":
        has_wildcard = any("*" in origin for origin in cors_origins)
        checks.append({
            "name": "CORS origins (production)",
            "valid": not has_wildcard,
            "message": "No wildcards" if not has_wildcard else "Wildcards not allowed in production",
        })
    else:
        checks.append({
            "name": "CORS origins",
            "valid": True,
            "message": f"{len(cors_origins)} origin(s) configured",
        })

    return checks


def _validate_external_services(env: str) -> List[Dict]:
    """Validate external service configuration."""
    checks = []

    # CEE configuration
    checks.append({
        "name": "CEE base URL",
        "valid": bool(settings.cee_base_url),
        "message": settings.cee_base_url if settings.cee_base_url else "Not configured",
    })

    if env == "production":
        checks.append({
            "name": "CEE API key",
            "valid": bool(settings.cee_api_key) and not settings.cee_use_mock,
            "message": "Configured" if settings.cee_api_key else "Missing for production",
        })
    else:
        checks.append({
            "name": "CEE mode",
            "valid": True,
            "message": "Mock" if settings.cee_use_mock else "Real",
        })

    # ISL configuration
    checks.append({
        "name": "ISL base URL",
        "valid": bool(settings.isl_base_url),
        "message": settings.isl_base_url if settings.isl_base_url else "Not configured",
    })

    if env == "production":
        checks.append({
            "name": "ISL API key",
            "valid": bool(settings.isl_api_key),
            "message": "Configured" if settings.isl_api_key else "Missing for production",
        })

    # PLoT configuration
    if settings.plot_deployment_mode:
        checks.append({
            "name": "PLoT internal API key",
            "valid": bool(settings.plot_internal_api_key) and len(settings.plot_internal_api_key) >= 32,
            "message": "Configured" if settings.plot_internal_api_key else "Missing",
        })

    return checks


def _validate_feature_flags() -> List[Dict]:
    """Validate Phase D feature flags."""
    checks = []

    features = {
        "D1: Portfolio Analytics": settings.feature_portfolio_analytics_enabled,
        "D2: Real-time Collaboration": settings.feature_realtime_collaboration_enabled,
        "D3: Decision Dependencies": settings.feature_decision_dependencies_enabled,
        "D4: Organizational Patterns": settings.feature_organizational_patterns_enabled,
        "D5: Advanced Analytics": settings.feature_advanced_analytics_enabled,
        "D6: Cross-Team Coordination": settings.feature_cross_team_coordination_enabled,
    }

    for feature_name, enabled in features.items():
        checks.append({
            "name": feature_name,
            "valid": True,  # Feature flags are always valid (just informational)
            "message": "Enabled" if enabled else "Disabled",
        })

    return checks
