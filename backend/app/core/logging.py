import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("geoattend")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def register_request_logging(app: FastAPI) -> None:
    """Structured per-request logging: request_id, route, status_code, duration.

    Never logs headers, tokens, or request/response bodies (docs/SECURITY.md §47).
    """

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s route=%s status_code=%s duration_ms=%s",
            request_id,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
