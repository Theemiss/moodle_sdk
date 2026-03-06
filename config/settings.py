"""Environment configuration using Pydantic Settings."""

from typing import Literal, Optional, Any
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    
    # Database connection settings - these will be loaded with DB_ prefix
    # Make non-critical fields optional with defaults
    host: str = Field("localhost", alias='db_host', validation_alias='db_host')
    port: int = Field(5432, alias='db_port', validation_alias='db_port')
    database: Optional[str] = Field(None, alias='db_name', validation_alias='db_name')
    username: Optional[str] = Field(None, alias='db_user', validation_alias='db_user')
    password: Optional[str] = Field(None, alias='db_password', validation_alias='db_password')
    
    # Renamed from 'schema' to avoid shadowing BaseSettings attribute
    db_schema: str = Field("public", alias='db_schema', validation_alias='db_schema')
    
    # Connection pool settings
    pool_min_size: int = Field(1, alias='db_pool_min_size', validation_alias='db_pool_min_size')
    pool_max_size: int = Field(10, alias='db_pool_max_size', validation_alias='db_pool_max_size')
    pool_timeout: int = Field(30, alias='db_pool_timeout', validation_alias='db_pool_timeout')
    statement_timeout: int = Field(30000, alias='db_statement_timeout', validation_alias='db_statement_timeout')
    
    # SSL settings
    ssl_mode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = Field(
        "prefer", alias='db_ssl_mode', validation_alias='db_ssl_mode'
    )
    ssl_ca_cert: Optional[str] = Field(None, alias='db_ssl_ca_cert', validation_alias='db_ssl_ca_cert')
    
    # Query engine settings
    query_timeout: int = Field(60, alias='db_query_timeout', validation_alias='db_query_timeout')
    max_rows: int = Field(10000, alias='db_max_rows', validation_alias='db_max_rows')
    safe_mode: bool = Field(True, alias='db_safe_mode', validation_alias='db_safe_mode')
    
    @property
    def db_host(self) -> str:
        return self.host
    
    @property
    def db_port(self) -> int:
        return self.port
    
    @property
    def db_name(self) -> Optional[str]:
        return self.database
    
    @property
    def db_user(self) -> Optional[str]:
        return self.username
    
    @property
    def db_password(self) -> Optional[str]:
        return self.password
    
    @property
    def db_schema(self) -> str:
        return self.db_schema
    
    # Backward compatibility property for 'schema'
    @property
    def schema(self) -> str:
        return self.db_schema

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DB_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class MoodleSettings(BaseSettings):
    """Moodle connection and behavior settings."""
    
    # Core settings - these will be loaded with MOODLE_ prefix
    url: str = Field(..., alias='moodle_url', validation_alias='moodle_url')
    token: str = Field(..., alias='moodle_token', validation_alias='moodle_token')
    service_name: str = Field(..., alias='moodle_service_name', validation_alias='moodle_service_name')
    
    # Request behavior
    request_timeout: int = Field(30, alias='moodle_request_timeout', validation_alias='moodle_request_timeout')
    max_retries: int = Field(3, alias='moodle_max_retries', validation_alias='moodle_max_retries')
    retry_backoff_factor: float = Field(0.5, alias='moodle_retry_backoff_factor', validation_alias='moodle_retry_backoff_factor')
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO", alias='moodle_log_level', validation_alias='moodle_log_level')
    log_format: Literal["json", "text"] = Field("json", alias='moodle_log_format', validation_alias='moodle_log_format')
    
    # Bulk operations
    bulk_chunk_size: int = Field(50, alias='moodle_bulk_chunk_size', validation_alias='moodle_bulk_chunk_size')
    
    # For backward compatibility, expose these as properties
    @property
    def moodle_url(self) -> str:
        return self.url
    
    @property
    def moodle_token(self) -> str:
        return self.token
    
    @property
    def moodle_service_name(self) -> str:
        return self.service_name
    
    @property
    def moodle_request_timeout(self) -> int:
        return self.request_timeout
    
    @property
    def moodle_max_retries(self) -> int:
        return self.max_retries
    
    @property
    def moodle_retry_backoff_factor(self) -> float:
        return self.retry_backoff_factor
    
    @property
    def moodle_log_level(self) -> str:
        return self.log_level
    
    @property
    def moodle_log_format(self) -> str:
        return self.log_format
    
    @property
    def moodle_bulk_chunk_size(self) -> int:
        return self.bulk_chunk_size
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MOODLE_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class Settings(BaseSettings):
    """Combined settings for the application."""
    
    moodle: MoodleSettings = Field(default_factory=MoodleSettings)
    database: Optional[DatabaseSettings] = Field(default=None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Only initialize database settings if DB_ env vars exist
        db_vars = [key for key in os.environ if key.startswith('DB_')]
        if db_vars:
            try:
                self.database = DatabaseSettings()
            except Exception as e:
                # Log but don't fail - database is optional
                import logging
                logging.getLogger(__name__).warning(f"Failed to initialize database settings: {e}")
                self.database = None
    
    # Backward compatibility properties for Moodle settings
    # This allows existing code to access settings.url, settings.token, etc.
    @property
    def url(self) -> str:
        return self.moodle.url
    
    @property
    def token(self) -> str:
        return self.moodle.token
    
    @property
    def service_name(self) -> str:
        return self.moodle.service_name
    
    @property
    def request_timeout(self) -> int:
        return self.moodle.request_timeout
    
    @property
    def max_retries(self) -> int:
        return self.moodle.max_retries
    
    @property
    def retry_backoff_factor(self) -> float:
        return self.moodle.retry_backoff_factor
    
    @property
    def log_level(self) -> str:
        return self.moodle.log_level
    
    @property
    def log_format(self) -> str:
        return self.moodle.log_format
    
    @property
    def bulk_chunk_size(self) -> int:
        return self.moodle.bulk_chunk_size
    
    # Backward compatibility properties for Moodle prefixed attributes
    @property
    def moodle_url(self) -> str:
        return self.moodle.url
    
    @property
    def moodle_token(self) -> str:
        return self.moodle.token
    
    @property
    def moodle_service_name(self) -> str:
        return self.moodle.service_name
    
    @property
    def moodle_request_timeout(self) -> int:
        return self.moodle.request_timeout
    
    @property
    def moodle_max_retries(self) -> int:
        return self.moodle.max_retries
    
    @property
    def moodle_retry_backoff_factor(self) -> float:
        return self.moodle.retry_backoff_factor
    
    @property
    def moodle_log_level(self) -> str:
        return self.moodle.log_level
    
    @property
    def moodle_log_format(self) -> str:
        return self.moodle.log_format
    
    @property
    def moodle_bulk_chunk_size(self) -> int:
        return self.moodle.bulk_chunk_size
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()