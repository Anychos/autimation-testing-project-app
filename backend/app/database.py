from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


pool_options = {}
if settings.metrics_enabled:
    from app.pool_metrics import InstrumentedPool, instrument_pool

    pool_options["poolclass"] = InstrumentedPool

engine = create_engine(
    settings.database_url, pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow, pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle, pool_pre_ping=settings.db_pool_pre_ping,
    **pool_options,
)
if settings.metrics_enabled:
    instrument_pool(engine.pool)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
