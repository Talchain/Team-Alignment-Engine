"""Secrets management with support for environment variables and AWS Secrets Manager."""

import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Unified secrets management supporting:
    - Environment variables (development)
    - AWS Secrets Manager (production)
    - Future: HashiCorp Vault, Azure Key Vault
    """

    def __init__(self, use_aws: bool = False, region: str = "us-east-1"):
        """
        Initialize secrets manager.

        Args:
            use_aws: Use AWS Secrets Manager instead of environment variables
            region: AWS region for Secrets Manager
        """
        self.use_aws = use_aws
        self.region = region
        self._aws_client = None

        if use_aws:
            try:
                import boto3
                from botocore.exceptions import ClientError
                self._aws_client = boto3.client(
                    'secretsmanager',
                    region_name=region
                )
                self._client_error = ClientError
                logger.info("AWS Secrets Manager initialized", extra={"region": region})
            except ImportError:
                logger.error("boto3 not installed. Install with: pip install boto3")
                raise RuntimeError("boto3 required for AWS Secrets Manager")
            except Exception as e:
                logger.error("Failed to initialize AWS Secrets Manager", exc_info=True)
                raise

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> str:
        """
        Get secret value from configured backend.

        Args:
            secret_name: Name of the secret (env var name or AWS secret name)
            default: Default value if secret not found

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found and no default provided
        """
        if self.use_aws:
            return self._get_from_aws(secret_name, default)
        else:
            return self._get_from_env(secret_name, default)

    def _get_from_env(self, secret_name: str, default: Optional[str] = None) -> str:
        """Get secret from environment variable."""
        value = os.getenv(secret_name, default)
        if value is None:
            raise ValueError(f"Secret not found: {secret_name}")
        return value

    def _get_from_aws(self, secret_name: str, default: Optional[str] = None) -> str:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self._aws_client.get_secret_value(SecretId=secret_name)

            # Secrets can be string or binary
            if 'SecretString' in response:
                secret = response['SecretString']
                # Try to parse as JSON (AWS stores structured secrets as JSON)
                try:
                    secret_dict = json.loads(secret)
                    # If JSON, return the whole dict as string
                    # In real usage, you'd specify which key to extract
                    return secret
                except json.JSONDecodeError:
                    return secret
            else:
                # Binary secret
                return response['SecretBinary'].decode('utf-8')

        except self._client_error as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Secret not found in AWS: {secret_name}")
                if default is not None:
                    return default
                raise ValueError(f"Secret not found: {secret_name}")
            else:
                logger.error(
                    f"AWS Secrets Manager error: {error_code}",
                    extra={"secret_name": secret_name},
                    exc_info=True
                )
                raise

    def get_secret_json(self, secret_name: str) -> Dict[str, Any]:
        """
        Get secret as JSON object (useful for structured secrets).

        Args:
            secret_name: Name of the secret

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If secret not found or not valid JSON
        """
        secret_string = self.get_secret(secret_name)
        try:
            return json.loads(secret_string)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse secret as JSON",
                extra={"secret_name": secret_name, "error": str(e)}
            )
            raise ValueError(f"Secret {secret_name} is not valid JSON")


# Global instance - initialized based on environment
def get_secrets_manager() -> SecretsManager:
    """
    Get secrets manager instance.

    In production, set environment variable:
        USE_AWS_SECRETS_MANAGER=true

    Returns:
        SecretsManager instance
    """
    use_aws = os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true"
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    return SecretsManager(use_aws=use_aws, region=aws_region)


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def init_secrets_manager() -> SecretsManager:
    """Initialize global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = get_secrets_manager()
    return _secrets_manager


def get_secret(secret_name: str, default: Optional[str] = None) -> str:
    """
    Convenience function to get secret from global manager.

    Args:
        secret_name: Name of the secret
        default: Default value if not found

    Returns:
        Secret value
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = init_secrets_manager()
    return _secrets_manager.get_secret(secret_name, default)
