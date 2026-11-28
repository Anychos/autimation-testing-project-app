from contextlib import asynccontextmanager
import logging
import sys
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.auth import router as auth_router
from app.tasks import router as tasks_router
from app.notification_proxy import router as notification_router
from app.errors import ERROR_RESPONSES, install_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    yield
    engine.dispose()


app = FastAPI(title="TaskFlow API", version="1.0.0", lifespan=lifespan)
install_handlers(app)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(notification_router)
if settings.metrics_enabled:
    from app.http_metrics import instrument_http

    instrument_http(app)


@app.middleware("http")
async def correlate_request(request: Request, call_next):
    try:
        correlation_id = UUID(request.headers.get("X-Correlation-ID", ""))
    except ValueError:
        correlation_id = uuid4()
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = str(correlation_id)
    return response

# FastAPI lists security dependencies as alternatives by default. Mutations
# require the cookie AND the CSRF header, so reflect that in the API contract.
default_openapi = app.openapi


def taskflow_openapi():
    schema = default_openapi()
    for path in schema["paths"].values():
        for operation in path.values():
            if not isinstance(operation, dict):
                continue
            security = operation.get("security", [])
            combined = {key: value for item in security for key, value in item.items()}
            if "APIKeyCookie" in combined and "APIKeyHeader" in combined:
                operation["security"] = [combined]
    return schema


app.openapi = taskflow_openapi


@app.get("/health", tags=["Health"], responses=ERROR_RESPONSES)
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
