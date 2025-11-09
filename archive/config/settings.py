"""
Application settings using Pydantic BaseSettings.
Loads configuration from environment variables.
"""

from typing import Literal, Optional
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="HiddenGem Trading System", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    secret_key: str = Field(default="", alias="SECRET_KEY")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/hiddengem",
        alias="DATABASE_URL"
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL"
    )
    redis_cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL")  # seconds
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # Data Sources
    tushare_token: Optional[str] = Field(default=None, alias="TUSHARE_TOKEN")
    akshare_enabled: bool = Field(default=True, alias="AKSHARE_ENABLED")
    joinquant_username: Optional[str] = Field(default=None, alias="JOINQUANT_USERNAME")
    joinquant_password: Optional[str] = Field(default=None, alias="JOINQUANT_PASSWORD")

    # Data source rate limits (requests per minute)
    tushare_rate_limit: int = Field(default=200, alias="TUSHARE_RATE_LIMIT")
    akshare_rate_limit: int = Field(default=60, alias="AKSHARE_RATE_LIMIT")

    # Trading
    broker_api_key: Optional[str] = Field(default=None, alias="BROKER_API_KEY")
    broker_api_secret: Optional[str] = Field(default=None, alias="BROKER_API_SECRET")
    trading_mode: Literal["simulation", "live"] = Field(
        default="simulation", alias="TRADING_MODE"
    )

    # Risk Management
    max_position_pct: float = Field(default=0.10, alias="MAX_POSITION_PCT")  # 10%
    max_sector_pct: float = Field(default=0.30, alias="MAX_SECTOR_PCT")  # 30%
    default_stop_loss_pct: float = Field(default=0.08, alias="DEFAULT_STOP_LOSS_PCT")  # 8%
    default_take_profit_pct: float = Field(default=0.15, alias="DEFAULT_TAKE_PROFIT_PCT")  # 15%

    # Compliance
    max_orders_per_second: int = Field(default=300, alias="MAX_ORDERS_PER_SECOND")
    max_orders_per_day: int = Field(default=20000, alias="MAX_ORDERS_PER_DAY")

    # MCP Configuration
    mcp_transport: Literal["stdio", "http", "websocket"] = Field(
        default="stdio", alias="MCP_TRANSPORT"
    )
    mcp_port: int = Field(default=8001, alias="MCP_PORT")
    mcp_timeout: int = Field(default=30, alias="MCP_TIMEOUT")  # seconds

    # LLM Configuration
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        alias="LLM_BASE_URL"
    )
    llm_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        alias="LLM_MODEL"
    )
    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    llm_timeout: int = Field(default=30, alias="LLM_TIMEOUT")  # seconds
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    api_reload: bool = Field(default=False, alias="API_RELOAD")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS"
    )

    # JWT
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that secret key is set in production."""
        if not v:
            import secrets
            # Generate a random secret key for development
            return secrets.token_urlsafe(32)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def database_url_async(self) -> str:
        """Get async database URL for SQLAlchemy."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or self.log_level == "DEBUG"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development


# Global settings instance
settings = Settings()
