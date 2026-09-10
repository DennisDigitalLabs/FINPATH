"""
FINPATH Backend Configuration Management

Handles environment-based configuration for database, security, and application settings.
Supports both PostgreSQL (production) and SQLite (development/testing).
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    Attributes:
        ENVIRONMENT: Application environment (development, testing, production)
        DEBUG: Debug mode flag
        DATABASE_URL: Database connection URL (PostgreSQL or SQLite)
        SQLALCHEMY_ECHO: Echo SQL queries for debugging
        SECRET_KEY: Secret key for JWT token signing
        ALGORITHM: JWT algorithm
        ACCESS_TOKEN_EXPIRE_MINUTES: JWT token expiration time
        CORS_ORIGINS: Allowed CORS origins
    """
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
    # Application Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./finpath.db"  # Default to SQLite for local development
    SQLITE_DB_PATH: str = "/var/lib/render/project/data/finpath.db"
    SQLALCHEMY_ECHO: bool = False
    
    # Security Configuration
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ML integration configuration. The path may point to the trained model directory
    # or a specific artifact file, depending on deployment needs.
    MODEL_PATH: str | None = None
    MODEL_VERSION: str | None = "v1"
    
    # CORS Configuration
    CORS_ORIGINS: list = ["http://localhost", "http://localhost:3000", "http://localhost:8080"]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if not value or value == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be configured through the environment")
        if len(value) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.is_production and self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        if self.is_production and "*" in self.CORS_ORIGINS:
            raise ValueError("Wildcard CORS origins are not allowed in production")
        return self
    
    def get_database_url(self) -> str:
        """
        Get the database URL, preferring an explicit DATABASE_URL when provided.

        For SQLite deployments we keep a single durable file path on Render's
        persistent disk and default to the local project file during development.

        Priority:
        1. DATABASE_URL environment variable
        2. PostgreSQL components (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
        3. Default SQLite database in the local project or Render persistent storage

        Returns:
            Database connection URL
        """
        if self.DATABASE_URL and self.DATABASE_URL != "sqlite:///./finpath.db":
            return self._normalize_database_url(self.DATABASE_URL)

        # Check for PostgreSQL environment variables
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")

        if all([db_user, db_password, db_host, db_name]):
            return self._normalize_database_url(
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )

        if self.is_production:
            return f"sqlite:///{self.SQLITE_DB_PATH}"

        # Default to SQLite in the project root for local development
        return self.DATABASE_URL

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        """Use psycopg 3 for PostgreSQL while preserving SQLite URLs."""
        if database_url.startswith("postgres://"):
            return "postgresql+psycopg://" + database_url[len("postgres://") :]
        if database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + database_url[len("postgresql://") :]
        return database_url
    
    @property
    def model_directory(self) -> Path:
        configured = self.MODEL_PATH
        if configured:
            return Path(configured).expanduser()
        return Path(__file__).resolve().parent.parent / "models" / "v1"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT.lower() == "testing"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    The cache ensures settings are loaded only once from environment variables.
    
    Returns:
        Settings object with all application configuration
    """
    return Settings()
