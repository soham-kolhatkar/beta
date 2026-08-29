import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.core.config import settings
from app.core.errors import ApiError
from app.core.geo import haversine_distance_meters
from app.models.attendance import Attendance
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_verification import AttendanceVerification, VerificationStatus
from app.models.student import Student
from app.repositories import (
    attendance_repository,
    attendance_session_repository,
    attendance_verification_repository,
    class_enrollment_repository,
    face_profile_repository,
)
from app.schemas.verification import (
    CompleteAttendanceResponse,
    FaceVerifyResponse,
    LocationVerifyRequest,
    LocationVerifyResponse,
)
from app.services import face_service


def _session_currently_active(session: AttendanceSession, now: datetime) -> bool:
    return session.status == SessionStatus.ACTIVE and session.starts_at <= now <= session.ends_at


async def start_verification(
    db: AsyncSession, student: Student, session_id: uuid.UUID
) -> AttendanceVerification:
    """docs/API.md §27: authenticated + enrolled + registered face +
    eligible for the session. Does not check for pre-existing attendance —
    that's the `/complete` step's job (§32), not a precondition for even
    starting a new attempt.
    """
    session = await attendance_session_repository.get_by_id(db, session_id)
    if session is None:
        raise ApiError("SESSION_NOT_FOUND", "Session not found.", status_code=404)

    enrollment = await class_enrollment_repository.get_by_class_and_student(
        db, session.class_id, student.id
    )
    if enrollment is None:
        raise ApiError("NOT_ENROLLED", "You are not enrolled in this class.", status_code=403)

    now = datetime.now(timezone.utc)
    if now < session.starts_at:
        raise ApiError("SESSION_NOT_ACTIVE", "This session hasn't started yet.", status_code=409)
    if not _session_currently_active(session, now):
        raise ApiError("SESSION_EXPIRED", "This attendance session has ended.", status_code=409)

    face_profile = await face_profile_repository.get_by_student_id(db, student.id)
    if face_profile is None:
        raise ApiError(
            "FACE_NOT_REGISTERED",
            "Please register your face before marking attendance.",
            status_code=409,
        )

    expires_at = now + timedelta(seconds=settings.verification_context_ttl_seconds)
    verification = await attendance_verification_repository.create(
        db, session.id, student.id, expires_at
    )
    await db.commit()
    return verification


async def submit_location(
    db: AsyncSession,
    student: Student,
    verification_id: uuid.UUID,
    payload: LocationVerifyRequest,
) -> LocationVerifyResponse:
    verification = await attendance_verification_repository.get_by_id(db, verification_id)

    # A wrong/unknown id and someone else's real id get the identical
    # response — don't confirm whether a verification exists for another
    # student (docs/API.md §40).
    if verification is None or verification.student_id != student.id:
        raise ApiError(
            "VERIFICATION_INVALID", "This verification link is invalid.", status_code=404
        )

    resubmittable = (VerificationStatus.CREATED, VerificationStatus.LOCATION_VERIFIED)
    if verification.status not in resubmittable:
        raise ApiError(
            "VERIFICATION_STEP_INVALID",
            "This verification is not currently accepting a location submission.",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    if now > verification.expires_at:
        verification.status = VerificationStatus.EXPIRED
        await db.commit()
        raise ApiError(
            "VERIFICATION_EXPIRED",
            "This verification has expired. Please try again.",
            status_code=409,
        )

    session = await attendance_session_repository.get_by_id(db, verification.session_id)

    distance_meters = haversine_distance_meters(
        payload.latitude, payload.longitude, session.latitude, session.longitude
    )
    within_radius = distance_meters <= session.radius_meters
    accuracy_ok = payload.accuracy_meters <= settings.location_max_accuracy_meters

    verification.location_latitude = payload.latitude
    verification.location_longitude = payload.longitude
    verification.location_accuracy_meters = payload.accuracy_meters
    verification.location_distance_meters = distance_meters

    if within_radius and accuracy_ok:
        verification.status = VerificationStatus.LOCATION_VERIFIED
        await db.commit()
        return LocationVerifyResponse(
            verified=True,
            distance_meters=round(distance_meters, 1),
            accuracy_meters=payload.accuracy_meters,
            next_step="FACE",
        )

    await db.commit()

    if not within_radius:
        code, message = "LOCATION_OUTSIDE_RADIUS", "You are outside the attendance area."
    else:
        code, message = (
            "LOCATION_ACCURACY_TOO_LOW",
            "Your location accuracy is too low. Move to an open area and try again.",
        )

    return LocationVerifyResponse(
        verified=False,
        distance_meters=round(distance_meters, 1),
        accuracy_meters=payload.accuracy_meters,
        code=code,
        message=message,
        allowed_radius_meters=session.radius_meters,
    )


async def submit_face(
    db: AsyncSession,
    student: Student,
    verification_id: uuid.UUID,
    content_type: str | None,
    raw: bytes,
) -> FaceVerifyResponse:
    verification = await attendance_verification_repository.get_by_id(db, verification_id)

    if verification is None or verification.student_id != student.id:
        raise ApiError(
            "VERIFICATION_INVALID", "This verification link is invalid.", status_code=404
        )

    resubmittable = (VerificationStatus.LOCATION_VERIFIED, VerificationStatus.FACE_VERIFIED)
    if verification.status not in resubmittable:
        raise ApiError(
            "VERIFICATION_STEP_INVALID",
            "Complete location verification before submitting a face.",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    if now > verification.expires_at:
        verification.status = VerificationStatus.EXPIRED
        await db.commit()
        raise ApiError(
            "VERIFICATION_EXPIRED",
            "This verification has expired. Please try again.",
            status_code=409,
        )

    # Guaranteed by start_verification, but re-checked here since the
    # embedding itself is needed anyway (docs/AGENTS.md rule 3: re-derive
    # security-sensitive state, don't just trust an earlier step happened).
    face_profile = await face_profile_repository.get_by_student_id(db, student.id)
    if face_profile is None:
        raise ApiError(
            "FACE_NOT_REGISTERED",
            "Please register your face before marking attendance.",
            status_code=409,
        )

    image = face_service.decode_image(content_type, raw)
    live_embedding = face_model.extract_embedding(image)
    distance = face_model.compare_embeddings(face_profile.embedding, live_embedding)
    verified = distance <= settings.face_similarity_threshold

    verification.face_similarity = distance

    if verified:
        verification.status = VerificationStatus.FACE_VERIFIED
        await db.commit()
        return FaceVerifyResponse(verified=True, next_step="COMPLETE")

    await db.commit()
    return FaceVerifyResponse(
        verified=False,
        code="FACE_NOT_VERIFIED",
        message="We couldn't verify your identity.",
        retryable=True,
    )


async def complete_verification(
    db: AsyncSession, student: Student, verification_id: uuid.UUID
) -> CompleteAttendanceResponse:
    """docs/API.md §32: revalidates everything from scratch even though
    earlier steps already passed — a verification context is not a promise,
    it's evidence the backend re-checks at the point attendance is actually
    granted.
    """
    verification = await attendance_verification_repository.get_by_id(db, verification_id)

    if verification is None or verification.student_id != student.id:
        raise ApiError(
            "VERIFICATION_INVALID", "This verification link is invalid.", status_code=404
        )

    now = datetime.now(timezone.utc)
    if now > verification.expires_at:
        if verification.status != VerificationStatus.EXPIRED:
            verification.status = VerificationStatus.EXPIRED
            await db.commit()
        raise ApiError(
            "VERIFICATION_EXPIRED",
            "This verification has expired. Please try again.",
            status_code=409,
        )

    session = await attendance_session_repository.get_by_id(db, verification.session_id)
    if not _session_currently_active(session, now):
        raise ApiError("SESSION_EXPIRED", "This attendance session has ended.", status_code=409)

    enrollment = await class_enrollment_repository.get_by_class_and_student(
        db, session.class_id, student.id
    )
    if enrollment is None:
        raise ApiError("NOT_ENROLLED", "You are not enrolled in this class.", status_code=403)

    if verification.status != VerificationStatus.FACE_VERIFIED:
        raise ApiError(
            "VERIFICATION_STEP_INVALID",
            "Complete location and face verification first.",
            status_code=409,
        )

    existing = await attendance_repository.get_by_session_and_student(db, session.id, student.id)
    if existing is not None:
        raise ApiError(
            "ATTENDANCE_ALREADY_MARKED",
            "Attendance has already been marked for this session.",
            status_code=409,
        )

    attendance = await _create_attendance_or_raise(db, verification, session, student, now)
    verification.status = VerificationStatus.COMPLETED
    await db.commit()
    return CompleteAttendanceResponse.from_attendance(attendance)


async def _create_attendance_or_raise(
    db: AsyncSession,
    verification: AttendanceVerification,
    session: AttendanceSession,
    student: Student,
    marked_at: datetime,
) -> Attendance:
    """The service-level `existing is not None` check above is the first
    line of defense; this is the second, for the race window between that
    check and this insert (docs/ARCHITECTURE.md §25) — the database's own
    UNIQUE(session_id, student_id) is the actual guarantee under
    concurrent requests.
    """
    try:
        return await attendance_repository.create(
            db,
            session_id=session.id,
            student_id=student.id,
            marked_at=marked_at,
            latitude=verification.location_latitude,
            longitude=verification.location_longitude,
            location_accuracy=verification.location_accuracy_meters,
            distance_meters=verification.location_distance_meters,
            face_verified=True,
            face_score=verification.face_similarity,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            "ATTENDANCE_ALREADY_MARKED",
            "Attendance has already been marked for this session.",
            status_code=409,
        ) from exc
