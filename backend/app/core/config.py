from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ADP API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "custom-question-model"
    emotion_model_base_url: str | None = None
    emotion_model_api_key: str | None = None

    # Local execution defaults. ``PORT`` is also accepted for managed hosts
    # such as Railway, which inject it at runtime.
    server_host: str = "0.0.0.0"
    server_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("SERVER_PORT", "PORT"),
    )

    # Resolve this relative to the backend project, rather than the process'
    # current directory.  IDE launch configurations commonly start from the
    # repository root, where the actual file is ``backend/.env``.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
