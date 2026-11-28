from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from notification_service.settings import get_settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_timeout=3,
    connect_args={"connect_timeout": 3, "options": "-c statement_timeout=4000"},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
