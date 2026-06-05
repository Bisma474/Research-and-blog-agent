"""Centralized settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration.

    Reads from environment variables and a .env file in the project root.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_title: str = "Research & Blog Crew API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    # Default local dev origins.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # Extra CORS origins injected via EXTRA_CORS_ORIGINS env (comma-separated).
    # On Render we set this to the deployed UI URL.
    extra_cors_origins: str = ""

    # Storage
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'runs.db'}"
    output_dir: Path = PROJECT_ROOT / "output"

    def effective_cors_origins(self) -> list[str]:
        extra = [o.strip() for o in self.extra_cors_origins.split(",") if o.strip()]
        return self.cors_origins + extra

    # Crew
    default_topic: str = "AI Agents in 2026"
    max_concurrent_runs: int = 2

    # LLM routing (consumed by crew.yaml / agent kwargs)
    model_config_file: str = str(PROJECT_ROOT / "pyproject.toml")


@lru_cache
def get_settings() -> Settings:
    return Settings()
