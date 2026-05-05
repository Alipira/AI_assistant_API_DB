"""Application configuration"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, computed_field
from functools import lru_cache
import urllib.parse


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ═══════════════════════════════════════════════════════════
    # Database Configuration
    # ═══════════════════════════════════════════════════════════
    host: str = Field(default="localhost", description="Database host")
    port: str = Field(default="5432", alias="PORT", description="Database port")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="postgres", alias="POSTGRES_DB")

    # ═══════════════════════════════════════════════════════════
    # Backend API Configuration
    # ═══════════════════════════════════════════════════════════

    base_url: str = Field(
        default="https://locanit.bulutco.cloud/",
        description="Backend API base URL (NOT the Swagger UI path)",
    )
    backend_api_key: str = Field(default="", description="API key for backend")
    backend_api_token: str = Field(default="", description="API token for backend")
    api_timeout: int = Field(default=10, description="API request timeout in seconds")

    # ═══════════════════════════════════════════════════════════
    # Authorization Service (optional)
    # ═══════════════════════════════════════════════════════════
    authz_check_url: str = Field(
        default="",
        description="URL of centralized authz service. Leave empty to use local policy check.",
    )

    # ═══════════════════════════════════════════════════════════
    # OpenAI / Metis Configuration
    # ═══════════════════════════════════════════════════════════
    openai_api_key: str = Field(default="sk-test-key", alias="OPENAI_API_KEY")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_API_BASE",
    )
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # ═══════════════════════════════════════════════════════════
    # Application Settings
    # ═══════════════════════════════════════════════════════════
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    max_query_rows: int = Field(default=1000)
    allowed_schemas: list[str] = Field(default=["public"])

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    # ── Computed fields ──────────────────────────────────────

    @computed_field
    @property
    def database_url(self) -> str:
        encoded_password = urllib.parse.quote_plus(self.postgres_password)
        return (
            f"postgresql://{self.postgres_user}:{encoded_password}"
            f"@{self.host}:{self.port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def backend_api_url(self) -> str:
        """Clean base URL with no trailing slash, ready to have paths appended."""
        return self.base_url.rstrip("/")

    # ── Validators ───────────────────────────────────────────

    @field_validator("base_url", "openai_api_base", mode="before")
    @classmethod
    def clean_urls(cls, v):
        if isinstance(v, str):
            return v.strip('"').strip("'").rstrip("/")
        return v

    @field_validator("host", mode="before")
    @classmethod
    def clean_host(cls, v):
        if isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    @field_validator("postgres_user", "postgres_password", "postgres_db", "openai_api_key", mode="before")
    @classmethod
    def clean_strings(cls, v):
        if isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    def display_config(self) -> str:
        masked_pw = "*" * len(self.postgres_password)
        masked_key = self.openai_api_key[:10] + "..." if len(self.openai_api_key) > 10 else "***"
        return f"""
Configuration Loaded:
═══════════════════════════════════════════════════════════
Database:
  Host:     {self.host}
  Port:     {self.port}
  User:     {self.postgres_user}
  Password: {masked_pw}
  Database: {self.postgres_db}

Backend API:
  URL:      {self.backend_api_url}
  Timeout:  {self.api_timeout}s
  Authz:    {self.authz_check_url or '(local policy check)'}

OpenAI / Metis:
  API Base: {self.openai_api_base}
  API Key:  {masked_key}
  Model:    {self.openai_model}

Application:
  Environment: {self.environment}
  Debug:       {self.debug}
═══════════════════════════════════════════════════════════
"""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    try:
        s = get_settings()
        print("✅ Configuration loaded successfully!")
        print(s.display_config())
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        import traceback
        traceback.print_exc()
