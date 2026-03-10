from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="UNSCRIPTED_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/unscripted"
    )
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    object_storage_bucket: str = "unscripted"
    temporal_target: str = "localhost:7233"
    temporal_task_queue: str = "unscripted-control-plane"
    bootstrap_temporal_schedules: bool = False
    agent_dispatch_interval_seconds: int = 60
    agent_dispatch_batch_size: int = 5
    calibration_interval_seconds: int = 900
    default_calibration_model: str = "conversation-escalation"
    auth_dev_subject: str = "dev-user"
    auth_dev_handle: str = "architect"
    service_token: str = "replace-me"
    agent_daily_token_hard_cap: int = 12000
    cohort_daily_token_hard_cap: int = 100000
    sentry_dsn: str | None = None
    api_title: str = "UnScripted API"
    auto_create_schema: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
