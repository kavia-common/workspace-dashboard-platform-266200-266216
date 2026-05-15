from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All values are env-driven to support different deployments without code changes.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="Workspace Dashboard Platform API", description="API service name.")
    app_version: str = Field(default="0.2.0", description="API service version.")
    environment: str = Field(default="development", description="Runtime environment identifier.")

    cors_allow_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins, or '*' for all.",
    )

    database_url: str = Field(
        ...,
        description=(
            "PostgreSQL connection string. Example: postgresql+psycopg://user:pass@host:5432/db"
        ),
        validation_alias="DATABASE_URL",
    )

    jwt_secret_key: str = Field(
        ...,
        description="JWT signing secret. Keep this secure and rotate when needed.",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    jwt_access_token_exp_minutes: int = Field(
        default=60 * 24 * 7, description="Access token expiry in minutes."
    )

    password_hash_scheme: str = Field(default="bcrypt", description="Passlib hashing scheme.")

    def get_cors_origins(self) -> List[str]:
        """Parse cors_allow_origins into a list."""
        raw = (self.cors_allow_origins or "").strip()
        if raw == "*" or raw == "":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
