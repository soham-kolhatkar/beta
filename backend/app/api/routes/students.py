from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.academic import StudentMeResponse
from app.schemas.face import FaceModelInfo, FaceRegisterResponse, FaceStatusResponse
from app.services import face_service, student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me", response_model=StudentMeResponse)
async def get_my_student_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Student:
    return await student_service.get_my_profile(db, current_user)


@router.post("/me/face", response_model=FaceRegisterResponse)
async def register_my_face(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FaceRegisterResponse:
    student = await student_service.get_my_profile(db, current_user)
    raw = await image.read()
    profile = await face_service.register_face(db, student, image.content_type, raw)
    return FaceRegisterResponse(
        face_registered=True,
        model=FaceModelInfo(name=profile.model_name, version=profile.model_version),
    )


@router.get("/me/face", response_model=FaceStatusResponse)
async def get_my_face_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> FaceStatusResponse:
    student = await student_service.get_my_profile(db, current_user)
    profile = await face_service.get_face_status(db, student)

    if profile is None:
        return FaceStatusResponse(registered=False)

    return FaceStatusResponse(
        registered=True,
        model=FaceModelInfo(name=profile.model_name, version=profile.model_version),
        updated_at=profile.updated_at,
    )
