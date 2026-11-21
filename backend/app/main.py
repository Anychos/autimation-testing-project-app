from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine
from app.auth import router as auth_router
from app.tasks import router as tasks_router
from app.errors import ERROR_RESPONSES, install_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(title="TaskFlow API", version="1.0.0", lifespan=lifespan)
install_handlers(app)
app.include_router(auth_router)
app.include_router(tasks_router)

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
