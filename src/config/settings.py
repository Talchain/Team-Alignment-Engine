"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Service
    service_name: str = "team-alignment-engine"
    service_version: str = "2.0.0"  # Phase D complete + PLoT integration
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

    # PLoT Integration (POC v02)
    plot_deployment_mode: bool = False  # Set to True for PLoT-orchestrated mode
    plot_internal_api_key: str = ""  # Internal API key for PLoT → TAE auth
    plot_orchestration_timeout: int = 10  # Timeout for orchestration endpoint (seconds)
    plot_capability_filtering: bool = True  # Enable capability-based filtering

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
    cors_origins: List[str] = ["http://localhost:3000"]

    # Phase D: WebSocket Configuration
    websocket_heartbeat_interval: int = 30  # seconds
    websocket_max_connections_per_session: int = 50
    websocket_idle_timeout: int = 300  # 5 minutes
    websocket_message_max_size: int = 1048576  # 1MB

    # Phase D: Analytics Configuration
    analytics_cache_ttl: int = 300  # 5 minutes
    patterns_cache_ttl: int = 604800  # 7 days
    portfolio_max_sessions: int = 500

    # Phase D: Performance Configuration
    request_timeout: int = 30  # seconds
    dependency_graph_timeout: int = 5  # seconds
    portfolio_query_timeout: int = 10  # seconds

    # Phase D: Feature Flags (POC v02 Priorities from Q6 Decision)
    feature_portfolio_analytics_enabled: bool = True  # D1 - MUST HAVE
    feature_realtime_collaboration_enabled: bool = False  # D2 - DEFERRED (HTTP polling only)
    feature_decision_dependencies_enabled: bool = True  # D3 - MUST HAVE
    feature_organizational_patterns_enabled: bool = True  # D4 - MUST HAVE
    feature_advanced_analytics_enabled: bool = False  # D5 - DEFERRED
    feature_cross_team_coordination_enabled: bool = False  # D6 - DEFERRED

    # Phase D: CEE Mock Configuration
    cee_use_mock: bool = True  # Set to false when real CEE ready

    def get_cors_origins(self) -> List[str]:
        """
        Parse and validate CORS origins from comma-separated string or list.

        Raises:
            ValueError: If wildcard (*) used in production
        """
        if isinstance(self.cors_origins, str):
            origins = [origin.strip() for origin in self.cors_origins.split(",")]
        else:
            origins = self.cors_origins

        # Validate: No wildcards in production
        if self.environment == "production":
            for origin in origins:
                if "*" in origin:
                    raise ValueError(
                        f"Wildcard CORS origins not allowed in production: {origin}"
                    )

        return origins


# Global settings instance
settings = Settings()
