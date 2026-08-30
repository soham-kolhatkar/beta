from fastapi import FastAPI, Request

from app.core.config import settings


def register_security_headers(app: FastAPI) -> None:
    """docs/SECURITY.md §41/§72. This is a pure JSON API (no HTML rendered
    here), so a CSP/Permissions-Policy has nothing to constrain on this side
    — those live on the frontend's own responses instead (see
    `frontend/next.config.ts`). What's meaningful for an API response:
    stopping a browser from MIME-sniffing a JSON body as something else,
    not leaking the full referring URL to third parties, and (in
    production, over real HTTPS) HSTS.
    """

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
