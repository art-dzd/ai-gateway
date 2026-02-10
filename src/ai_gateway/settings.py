"""Настройки приложения (env + `.env`)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic-настройки (всё, что обычно лежит в `.env`)."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+psycopg://gateway:gateway@postgres:5432/gateway",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", validation_alias="REDIS_URL")

    default_provider: str = Field(default="mock", validation_alias="DEFAULT_PROVIDER")

    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_timeout_seconds: float = Field(default=30.0, validation_alias="OPENAI_TIMEOUT_SECONDS")
    openai_retries: int = Field(default=2, validation_alias="OPENAI_RETRIES")
    openai_http_referer: str | None = Field(default=None, validation_alias="OPENAI_HTTP_REFERER")
    openai_title: str | None = Field(default=None, validation_alias="OPENAI_TITLE")

    dashboard_login: str = Field(default="admin", validation_alias="DASHBOARD_LOGIN")
    dashboard_password: str = Field(default="admin", validation_alias="DASHBOARD_PASSWORD")

    default_rpm_limit: int = Field(default=60, validation_alias="DEFAULT_RPM_LIMIT")

    models_cache_ttl_seconds: int = Field(default=3600, validation_alias="MODELS_CACHE_TTL_SECONDS")

    celery_broker_url: str | None = Field(default=None, validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(
        default=None,
        validation_alias="CELERY_RESULT_BACKEND",
    )

    webhook_timeout_seconds: float = Field(default=10.0, validation_alias="WEBHOOK_TIMEOUT_SECONDS")
    worker_metrics_port: int | None = Field(default=None, validation_alias="WORKER_METRICS_PORT")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Ленивая загрузка настроек (один раз на процесс)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
