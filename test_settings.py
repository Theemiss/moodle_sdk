from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Print current environment
print("Current directory:", os.getcwd())
print(".env exists:", os.path.exists(".env"))

if os.path.exists(".env"):
    with open(".env", "r") as f:
        print("\n.env contents:")
        for line in f:
            if "TOKEN" not in line.upper():
                print(line.strip())
            else:
                print(line.split('=')[0] + "=********")

class TestSettings(BaseSettings):
    # These field names match the suffix after MOODLE_
    url: str  # Will look for MOODLE_URL
    token: str  # Will look for MOODLE_TOKEN
    service_name: str  # Will look for MOODLE_SERVICE_NAME
    
    # Optional fields with defaults
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    log_level: str = "INFO"
    log_format: str = "json"
    bulk_chunk_size: int = 50
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MOODLE_",  # This adds MOODLE_ prefix to all field names
        case_sensitive=False,
        extra="ignore",  # This allows extra fields without error
    )

try:
    settings = TestSettings()
    print("\n✓ Settings loaded successfully!")
    print(f"URL: {settings.url}")
    print(f"Service: {settings.service_name}")
    print(f"Timeout: {settings.request_timeout}")
    print(f"Log Level: {settings.log_level}")
except Exception as e:
    print(f"\n✗ Error: {e}")