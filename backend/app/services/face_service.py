import cv2
import deepface
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.core.config import settings
from app.core.errors import ApiError
from app.models.face_profile import FaceProfile
from app.models.student import Student
from app.repositories import face_profile_repository

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _decode_image(content_type: str | None, raw: bytes) -> np.ndarray:
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ApiError(
            "INVALID_REQUEST",
            "Unsupported image type. Please upload a JPEG, PNG, or WebP image.",
            status_code=422,
        )

    if len(raw) > settings.face_upload_max_bytes:
        raise ApiError("INVALID_REQUEST", "Image is too large.", status_code=422)

    # Decode via OpenCV rather than trusting the declared content-type
    # (docs/SECURITY.md §40: never trust the client-provided extension/type).
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ApiError(
            "INVALID_REQUEST", "That file couldn't be read as an image.", status_code=422
        )

    height, width = image.shape[:2]
    min_dimension = settings.face_min_image_dimension_px
    if height < min_dimension or width < min_dimension:
        raise ApiError(
            "INVALID_REQUEST",
            f"Image is too small (minimum {settings.face_min_image_dimension_px}px per side).",
            status_code=422,
        )

    return image


async def register_face(
    db: AsyncSession, student: Student, content_type: str | None, raw: bytes
) -> FaceProfile:
    image = _decode_image(content_type, raw)
    embedding = face_model.extract_embedding(image)

    profile = await face_profile_repository.upsert(
        db,
        student_id=student.id,
        embedding=embedding,
        model_name=settings.face_model_name,
        model_version=deepface.__version__,
    )
    student.face_registered = True
    await db.commit()
    return profile


async def get_face_status(db: AsyncSession, student: Student) -> FaceProfile | None:
    return await face_profile_repository.get_by_student_id(db, student.id)
