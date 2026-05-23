"""Application settings loaded from environment (see `.env.example` at repo root)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="postgresql+asyncpg://elena:elena_dev@localhost:5432/elena")
    redis_url: str = Field(default="redis://localhost:6379/0")

    auth_mode: Literal["development", "jwks"] = "development"
    jwt_audience: str | None = None
    jwks_url: str | None = None

    blob_storage_root: Path = Field(default=Path("./data/blob"))
    file_download_signing_secret: str = Field(
        default="dev-insecure-download-secret-change-me",
        min_length=8,
        description="HMAC secret for time-limited file download URLs",
    )

    # Public origin for clients (Compose: http://localhost:8000)
    public_api_base_url: str = Field(default="http://localhost:8000")

    compile_timeout_seconds: int = 90
    compile_quota_per_minute_per_user: int = 60

    import_max_pdf_bytes: int = 6_000_000
    import_max_extracted_chars: int = 200_000
    import_upload_quota_per_minute_per_user: int = 40
    import_llm_quota_per_minute_per_user: int = 20
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    expose_prometheus_metrics: bool = Field(
        default=False,
        description="Expose ``GET /metrics`` Prometheus scrape text (protect with network ACL in prod)",
    )

    llm_api_base_url: str | None = Field(default=None, description="OpenAI-compatible API base")
    llm_api_key: str | None = Field(default=None, description="BYOK; never log this value")
    llm_model: str = Field(default="gpt-4o-mini")

    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key; never log")
    gemini_model: str = Field(default="gemini-3.5-flash", description="Gemini model id for agent + LLM routes")

    agent_turn_quota_per_minute_per_user: int = Field(
        default=40,
        description="Redis rate limit bucket for synchronous editor agent POST /agent/turn",
    )

    jd_max_plaintext_chars: int = Field(
        default=200_000,
        description="Max character length for pasted job description on variant fork",
    )

    @property
    def psycopg_checkpoint_conninfo(self) -> str:
        """Connection URI for psycopg-based services (LangGraph ``AsyncPostgresSaver`` pool)."""

        u = self.database_url_sync_psycopg
        if "+psycopg" in u:
            return u.replace("postgresql+psycopg", "postgresql", 1)
        return u

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_sync_psycopg(self) -> str:
        """Sync driver URL for Alembic (postgresql+asyncpg -> postgresql+psycopg)."""
        u = self.database_url
        if "+asyncpg" in u:
            return u.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        return u.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
