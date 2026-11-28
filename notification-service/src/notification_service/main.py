from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from notification_service.api import router
from notification_service.api_schemas import ErrorOut, HealthOut
from notification_service.database import engine
from notification_service.errors import install_handlers
from notification_service.logging_config import configure_logging
from notification_service.models import Delivery, Notification
from notification_service.settings import get_settings


@asynccontextmanager
async def lifespan(_app):
    configure_logging()
    yield
    engine.dispose()


app = FastAPI(title="TaskFlow Notification API", version="1.0.0", lifespan=lifespan)
install_handlers(app)
app.include_router(router)
if get_settings().metrics_enabled:
    from notification_service.backlog_metrics import register_backlog
    from notification_service.http_metrics import instrument_http

    instrument_http(app)
    register_backlog()


@app.get("/health/live", tags=["Health"])
def liveness() -> HealthOut:
    return HealthOut()


@app.get("/health/ready", tags=["Health"], responses={503: {"model": ErrorOut}})
def readiness() -> HealthOut:
    with engine.connect() as connection:
        connection.execute(select(Notification.id).limit(0))
        connection.execute(select(Delivery.id).limit(0))
    return HealthOut()
