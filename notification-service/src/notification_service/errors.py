import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from notification_service.api_schemas import ErrorBody, ErrorDetail, ErrorOut
from notification_service.logging_config import log


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status = status
        self.error = ErrorBody(code=code, message=message, details=details or [])


def error_response(error: ApiError):
    data = ErrorOut(error=error.error)
    return JSONResponse(data.model_dump(mode="json"), status_code=error.status)


def install_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        details = [
            ErrorDetail(loc=list(error["loc"]), msg=error["msg"], type=error["type"])
            for error in exc.errors()
        ]
        return error_response(ApiError(422, "VALIDATION_ERROR", "Invalid request data", details))

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(_request: Request, exc: SQLAlchemyError):
        log("notification-api", "Database operation failed", level=logging.WARNING,
            error_type=type(exc).__name__)
        return error_response(ApiError(503, "DATABASE_UNAVAILABLE", "Database unavailable"))

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        return error_response(ApiError(exc.status_code, "HTTP_ERROR", str(exc.detail)))

    @app.exception_handler(Exception)
    async def internal(_request: Request, exc: Exception):
        log("notification-api", "Unexpected API error", level=logging.ERROR,
            error_type=type(exc).__name__)
        return error_response(ApiError(500, "INTERNAL_ERROR", "Internal server error"))
