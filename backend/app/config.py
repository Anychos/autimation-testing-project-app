from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    db_host: str = "localhost"
    postgres_db: str = "taskflow"
    postgres_user: str = "taskflow"
    postgres_password: str
    metrics_enabled: bool = False
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: float = Field(default=30, gt=0)
    db_pool_recycle: int = Field(default=-1, ge=-1)
    db_pool_pre_ping: bool = True
    http_connect_timeout: float | None = Field(default=None, gt=0)
    http_read_timeout: float | None = Field(default=None, gt=0)
    outbox_batch_size: int = Field(default=1, ge=1, le=1000)
    outbox_poll_interval: float = Field(default=1, gt=0)
    session_hours: int = Field(default=24, ge=1, le=8760)
    cookie_secure: bool = False
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )
    notifications_enabled: bool = False
    notification_api_url: str = "http://notification-api:8000"
    notification_api_timeout: float = Field(default=2, gt=0, le=10)
    internal_service_token: SecretStr = SecretStr("")
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "taskflow"
    rabbitmq_password: SecretStr = SecretStr("")
    rabbitmq_vhost: str = "taskflow"
    rabbitmq_exchange: str = "taskflow.events"
    rabbitmq_queue: str = "notification.events"

    @property
    def database_url(self) -> URL:
        return URL.create("postgresql+psycopg", username=self.postgres_user,
                          password=self.postgres_password, host=self.db_host,
                          database=self.postgres_db)

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
