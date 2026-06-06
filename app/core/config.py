"""
Configuration Management

Loads and validates all application settings from environment variables.
Uses Pydantic for type safety and validation.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are validated on application startup.
    Missing required variables will raise ValidationError.
    """
    
    # Application
    APP_NAME: str = "TradeMind AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production"] = Field(
        default="development",
        description="Runtime environment"
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity"
    )
    
    # API Server
    API_HOST: str = Field(default="0.0.0.0", description="API bind address")
    API_PORT: int = Field(default=8001, description="API port")
    
    # Supabase Database
    SUPABASE_DATABASE_URL: str = Field(
        ...,
        description="Supabase PostgreSQL connection string"
    )
    DB_POOL_SIZE: int = Field(default=10, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Recycle connections (seconds)")
    DB_ECHO: bool = Field(default=False, description="Log SQL queries")
    
    # Redis Cache
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Redis pool size")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, description="Socket timeout (seconds)")
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable metrics export")
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, description="Health check timeout (seconds)")
    
    # Groq LLM
    GROQ_API_KEY: str = Field(
        ...,
        description="Groq API key for LLM access"
    )
    GROQ_DEFAULT_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default Groq model"
    )
    
    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8001"],
        description="Allowed CORS origins"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
