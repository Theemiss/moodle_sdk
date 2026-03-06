"""Environment configuration using Pydantic Settings."""

from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MoodleSettings(BaseSettings):
    """Moodle connection and behavior settings."""
    
    # Core settings - these will be loaded with MOODLE_ prefix
    url: str = Field(..., alias='moodle_url', validation_alias='moodle_url')  # Can be accessed as .url or .moodle_url
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
    
    # For backward compatibility, also expose these as properties
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
        populate_by_name=True,  # This allows both name and alias to work
    )


# Global settings instance
settings = MoodleSettings()