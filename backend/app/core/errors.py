import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("geoattend")


class ApiError(Exception):
    """Raised by services/routes to produce the API's standard error envelope.

    See docs/API.md §52: {"error": {"code": "...", "message": "..."}}.
    """

    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            401: "AUTH_REQUIRED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "INVALID_REQUEST")
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
        return JSONResponse(status_code=exc.status_code, content=_error_body(code, message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "VALIDATION_ERROR", "Request validation failed.", {"errors": exc.errors()}
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        # Internal exception details are logged, never returned to the client
        # (docs/SECURITY.md §48).
        logger.exception("Unhandled error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "Something went wrong. Please try again."),
        )
