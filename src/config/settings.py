"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Service
    service_name: str = "team-alignment-engine"
    service_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str
    redis_pool_size: int = 10
    redis_cache_ttl: int = 3600

    # CEE Integration
    cee_base_url: str
    cee_api_key: str
    cee_timeout: int = 30

    # ISL Integration
    isl_base_url: str
    isl_api_key: str
    isl_timeout: int = 60

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Monitoring
    prometheus_port: int = 9090
    enable_metrics: bool = True

    # CORS
    cors_origins: Union[str, List[str]] = "http://localhost:3000"

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins


# Global settings instance
settings = Settings()
