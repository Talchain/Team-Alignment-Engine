"""Secrets management for Render deployment with environment variables.

Render provides built-in secrets management through encrypted environment
variables. No external secrets manager (AWS, Vault, etc.) is needed.

Documentation: https://render.com/docs/configure-environment-variables
"""

import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Secrets manager for Render deployment.

    Render automatically encrypts environment variables at rest and in transit.
    Secrets are managed via:
    1. Render Dashboard > Environment > Environment Variables
    2. Secret Files (for .env, certificates, etc.)
    3. Pull Secrets (for private Docker registries)

    All secrets are encrypted and only decrypted in your running service.
    """

    def __init__(self):
        """Initialize secrets manager for Render."""
        logger.info("Secrets manager initialized (Render environment variables)")

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> str:
        """
        Get secret value from environment variable.

        Args:
            secret_name: Name of the environment variable
            default: Default value if secret not found

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found and no default provided

        Example:
            >>> secrets = SecretsManager()
            >>> jwt_secret = secrets.get_secret("JWT_SECRET")
            >>> db_url = secrets.get_secret("DATABASE_URL")
        """
        value = os.getenv(secret_name, default)
        if value is None:
            logger.error(
                f"Secret not found: {secret_name}",
                extra={"secret_name": secret_name}
            )
            raise ValueError(
                f"Required secret '{secret_name}' not found in environment. "
                f"Configure it in Render Dashboard > Environment."
            )
        return value

    def get_secret_or_none(self, secret_name: str) -> Optional[str]:
        """
        Get secret value, returning None if not found.

        Args:
            secret_name: Name of the environment variable

        Returns:
            Secret value or None

        Example:
            >>> secrets = SecretsManager()
            >>> optional_key = secrets.get_secret_or_none("OPTIONAL_API_KEY")
        """
        return os.getenv(secret_name)

    def require_secrets(self, *secret_names: str) -> None:
        """
        Validate that required secrets are present on startup.

        Args:
            *secret_names: Names of required environment variables

        Raises:
            ValueError: If any required secret is missing

        Example:
            >>> secrets = SecretsManager()
            >>> secrets.require_secrets(
            ...     "JWT_SECRET",
            ...     "DATABASE_URL",
            ...     "REDIS_URL"
            ... )
        """
        missing = []
        for secret_name in secret_names:
            if not os.getenv(secret_name):
                missing.append(secret_name)

        if missing:
            error_msg = (
                f"Missing required secrets: {', '.join(missing)}\n"
                f"Configure these in Render Dashboard > Environment > Environment Variables"
            )
            logger.error(error_msg, extra={"missing_secrets": missing})
            raise ValueError(error_msg)

        logger.info(
            f"All required secrets validated: {len(secret_names)} secrets found",
            extra={"secret_count": len(secret_names)}
        )


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get the global secrets manager instance.

    Returns:
        SecretsManager instance
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(secret_name: str, default: Optional[str] = None) -> str:
    """
    Convenience function to get secret from global manager.

    Args:
        secret_name: Name of the secret
        default: Default value if not found

    Returns:
        Secret value

    Example:
        >>> from src.config.secrets import get_secret
        >>> jwt_secret = get_secret("JWT_SECRET")
    """
    return get_secrets_manager().get_secret(secret_name, default)


def validate_production_secrets() -> None:
    """
    Validate all required secrets for production deployment.

    Call this on application startup to fail fast if secrets are missing.

    Raises:
        ValueError: If any required secret is missing
    """
    secrets = get_secrets_manager()

    required_secrets = [
        # Core application
        "JWT_SECRET",
        "DATABASE_URL",
        "REDIS_URL",

        # External services
        "CEE_BASE_URL",
        "CEE_API_KEY",
        "ISL_BASE_URL",
        "ISL_API_KEY",

        # PLoT integration
        "PLOT_INTERNAL_API_KEY",
    ]

    secrets.require_secrets(*required_secrets)
    logger.info("Production secrets validation complete ✓")
