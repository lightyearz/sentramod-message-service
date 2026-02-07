"""
Configuration for Message Service
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
import os


from typing import List

class Settings(BaseSettings):
    """Application settings"""

    # Service Info
    SERVICE_NAME: str = "message-service"
    SERVICE_VERSION: str = "1.0.0"
    API_PORT: int = 8007

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://modai:modai@localhost:5432/modai",
    )

    # External Services
    TOPIC_CLASSIFIER_URL: str = os.getenv("TOPIC_CLASSIFIER_URL", "http://localhost:8004")
    CONSENT_SERVICE_URL: str = os.getenv("CONSENT_SERVICE_URL", "http://localhost:8006")

    # CORS - supports comma or ^@^ separator (Cloud Run uses ^@^ for env vars with commas)
    CORS_ORIGINS: List[str] | str = ["http://localhost:3000", "http://localhost:8001"]

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated or ^@^-separated string or list"""
        if isinstance(v, str):
            # Cloud Run uses ^@^ as separator for values with commas
            if '^@^' in v:
                return [origin.strip() for origin in v.split('^@^')]
            return [origin.strip() for origin in v.split(',')]
        return v

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


# Global settings instance
settings = Settings()
