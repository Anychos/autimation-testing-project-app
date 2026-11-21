from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    db_host: str = "localhost"
    postgres_db: str = "taskflow"
    postgres_user: str = "taskflow"
    postgres_password: str
    session_hours: int = Field(default=24, ge=1, le=8760)
    cookie_secure: bool = False
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )

    @property
    def database_url(self) -> URL:
        return URL.create("postgresql+psycopg", username=self.postgres_user,
                          password=self.postgres_password, host=self.db_host,
                          database=self.postgres_db)

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
