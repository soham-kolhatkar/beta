import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_profile import FaceProfile


async def get_by_student_id(db: AsyncSession, student_id: uuid.UUID) -> FaceProfile | None:
    result = await db.execute(select(FaceProfile).where(FaceProfile.student_id == student_id))
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    student_id: uuid.UUID,
    embedding: list[float],
    model_name: str,
    model_version: str,
) -> FaceProfile:
    profile = await get_by_student_id(db, student_id)

    if profile is None:
        profile = FaceProfile(
            student_id=student_id,
            embedding=embedding,
            model_name=model_name,
            model_version=model_version,
        )
        db.add(profile)
    else:
        profile.embedding = embedding
        profile.model_name = model_name
        profile.model_version = model_version

    await db.flush()
    return profile
