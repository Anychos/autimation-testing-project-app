import logging
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

logger = logging.getLogger("uvicorn.error")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[Any] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


ERROR_RESPONSES = {code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 422, 500)}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def response(status, code, message, details=None):
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "details": details or []}})


def install_handlers(app):
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo passwords or other input values into error responses.
        details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return response(422, "VALIDATION_ERROR", "Invalid request data", jsonable_encoder(details))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return response(exc.status_code, {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(
            exc.status_code, "HTTP_ERROR"), str(exc.detail))

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s %s", request.method, request.url.path)
        return response(500, "INTERNAL_ERROR", "Internal server error")
