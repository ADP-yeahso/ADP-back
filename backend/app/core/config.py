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
    supabase_storage_bucket: str = "diary-media"
    # Directory containing the fine-tuned KoBART question-generation model.
    # This can be a Railway Volume mount such as /models/question.
    question_model_path: str = "app/model_artifacts/question"
    # Railway's CPU instances run this model synchronously.  Keep the
    # generated question short enough to return within the web client's
    # request window; these questions are normally one sentence.
    question_max_new_tokens: int = 32
    question_num_beams: int = 1
    # Directory containing config.json, model.safetensors and tokenizer files.
    # This can be a Railway Volume mount such as /models/emotion.
    emotion_model_path: str = "app/model_artifacts/emotion"
    # Maps the model's saved labels (for example LABEL_0) to the application's
    # emotion codes. The saved checkpoint uses generic labels, so this is
    # intentionally required at deployment time.
    emotion_label_map: dict[str, str] = Field(default_factory=dict)
    # --- MLOps (optional) ---------------------------------------------------
    # When set, the emotion model is downloaded from this Hugging Face repository
    # (for example "user/moaon-emotion-kcelectra") instead of EMOTION_MODEL_PATH.
    # EMOTION_MODEL_PATH stays as the fallback when the download fails.
    emotion_model_hf_repo: str | None = None
    # Read-only Hugging Face token (needed for private repositories).
    emotion_model_hf_token: str | None = None
    # Pin a revision such as "v2". Empty = the 'deployed' row of model_registry.
    emotion_model_revision: str | None = None
    # Where downloaded revisions are stored. On Railway, use the volume, e.g.
    # /models/emotion-hf, so restarts do not download the model again.
    emotion_model_cache_dir: str = "app/model_artifacts/emotion-hf"
    # Shared secret the training job sends in X-Reload-Token to POST /reload-model.
    # The endpoint is disabled while this is empty.
    emotion_model_reload_token: str | None = None

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
