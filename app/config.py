"""Application configuration - Works with custom OpenAI endpoints"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, computed_field
from functools import lru_cache
from typing import Optional
import urllib.parse


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ═══════════════════════════════════════════════════════════
    # Database Configuration (Separate Parameters)
    # ═══════════════════════════════════════════════════════════
    host: str = Field(default="localhost", description="Database host")
    port: str = Field(default="5432", alias="PORT", description="Database port")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER", description="Database user")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD", description="Database password")
    postgres_db: str = Field(default="postgres", alias="POSTGRES_DB", description="Database name")

    # ═══════════════════════════════════════════════════════════
    # Backend API Configuration
    # ═══════════════════════════════════════════════════════════
    base_url: str = Field(
        default="http://localhost:8080",
        description="Backend API base URL"
    )
    backend_api_key: str = Field(default="", description="API key for backend")
    backend_api_token: str = Field(default="", description="API token for backend")
    api_timeout: int = Field(default=10, description="API request timeout in seconds")

    # ═══════════════════════════════════════════════════════════
    # OpenAI Configuration (Supports Custom Endpoints)
    # ═══════════════════════════════════════════════════════════
    openai_api_key: str = Field(
        default="sk-test-key",
        description="OpenAI API key (or compatible service key)"
    )
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL (use custom endpoint if needed)",
        alias="OPENAI_API_BASE"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )

    # ═══════════════════════════════════════════════════════════
    # Application Settings
    # ═══════════════════════════════════════════════════════════
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=True, description="Debug mode")

    # ═══════════════════════════════════════════════════════════
    # Security Settings
    # ═══════════════════════════════════════════════════════════
    max_query_rows: int = Field(default=1000, description="Max rows per query")
    allowed_schemas: list[str] = Field(
        default=["public"],
        description="Allowed database schemas"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @computed_field
    @property
    def database_url(self) -> str:
        """
        Build PostgreSQL connection URL from separate parameters
        Automatically URL-encodes special characters in password
        """
        encoded_password = urllib.parse.quote_plus(self.postgres_password)
        url = f"postgresql://{self.postgres_user}:{encoded_password}@{self.host}:{self.port}/{self.postgres_db}"
        return url

    @computed_field
    @property
    def backend_api_url(self) -> str:
        """
        Get backend API URL (alias for base_url)
        Removes trailing slash if present
        """
        return self.base_url.rstrip('/')

    @field_validator('base_url', 'openai_api_base', mode='before')
    @classmethod
    def clean_urls(cls, v):
        """Remove quotes and trailing slashes from URLs"""
        if isinstance(v, str):
            return v.strip('"').strip("'").rstrip('/')
        return v

    @field_validator('host', mode='before')
    @classmethod
    def clean_host(cls, v):
        """Remove quotes from host if present"""
        if isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    @field_validator('postgres_user', 'postgres_password', 'postgres_db', 'openai_api_key', mode='before')
    @classmethod
    def clean_strings(cls, v):
        """Remove quotes from string fields if present"""
        if isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    def display_config(self) -> str:
        """Display configuration (with masked sensitive data)"""
        masked_password = '*' * len(self.postgres_password)
        masked_api_key = self.openai_api_key[:10] + '...' if len(self.openai_api_key) > 10 else '***'

        return f"""
Configuration Loaded:
═══════════════════════════════════════════════════════════
Database:
  Host: {self.host}
  Port: {self.port}
  User: {self.postgres_user}
  Password: {masked_password}
  Database: {self.postgres_db}
  Full URL: postgresql://{self.postgres_user}:{masked_password}@{self.host}:{self.port}/{self.postgres_db}

Backend API:
  URL: {self.backend_api_url}
  Timeout: {self.api_timeout}s

OpenAI:
  API Base: {self.openai_api_base}
  API Key: {masked_api_key}
  Model: {self.openai_model}

Application:
  Environment: {self.environment}
  Debug: {self.debug}
═══════════════════════════════════════════════════════════
"""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


if __name__ == "__main__":
    try:
        settings = get_settings()
        print("✅ Configuration loaded successfully!")
        print(settings.display_config())
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        import traceback
        traceback.print_exc()