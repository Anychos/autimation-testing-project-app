from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    metrics_enabled: bool = False
    rabbitmq_prefetch: int = Field(default=1, ge=1, le=65535)
    smtp_delivery_concurrency: int = Field(default=1, ge=1, le=32)
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    postgres_host: str = "notification-db"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "notifications"
    postgres_user: str = "notifications"
    postgres_password: SecretStr
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = Field(default=5672, ge=1, le=65535)
    rabbitmq_user: str = "taskflow"
    rabbitmq_password: SecretStr
    rabbitmq_vhost: str = "taskflow"
    rabbitmq_exchange: str = "taskflow.events"
    rabbitmq_queue: str = "notification.events"
    event_max_retries: int = Field(default=3, ge=0)
    event_retry_interval_seconds: str = "5,15,30"
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_from_email: str = "notifications@taskflow.test"
    smtp_from_name: str = "TaskFlow"
    smtp_use_tls: bool = False
    smtp_use_ssl: bool = False
    smtp_timeout: float = Field(default=5, gt=0, le=10)
    email_enabled: bool = True
    email_max_retries: int = Field(default=3, ge=0)
    email_retry_interval_seconds: int = Field(default=5, gt=0)
    internal_service_token: SecretStr = Field(min_length=16)

    @property
    def retry_intervals(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self.event_retry_interval_seconds.split(","))

    @model_validator(mode="after")
    def validate_modes(self) -> Self:
        intervals = self.retry_intervals
        if any(i <= 0 for i in intervals) or len(set(intervals)) != len(intervals):
            raise ValueError("Event retry intervals must be distinct positive seconds")
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("Choose either STARTTLS or implicit TLS")
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg", self.postgres_user, self.postgres_password.get_secret_value(),
            self.postgres_host, self.postgres_port, self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
