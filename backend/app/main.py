from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 (registers all models with SQLAlchemy — see app/models/__init__.py)
from app.api.routes import attendance, auth, faculty, health, students
from app.core import face_model
from app.core import redis as redis_client
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, register_request_logging
from app.core.security_headers import register_security_headers

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    face_model.warm_up()
    await redis_client.init()
    yield
    await redis_client.close()


app = FastAPI(title="GeoAttend API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_request_logging(app)
register_security_headers(app)
register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(faculty.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
