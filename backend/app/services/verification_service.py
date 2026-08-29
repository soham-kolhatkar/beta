import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ApiError
from app.core.geo import haversine_distance_meters
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_verification import AttendanceVerification, VerificationStatus
from app.models.student import Student
from app.repositories import (
    attendance_session_repository,
    attendance_verification_repository,
    class_enrollment_repository,
    face_profile_repository,
)
from app.schemas.verification import LocationVerifyRequest, LocationVerifyResponse


def _session_currently_active(session: AttendanceSession, now: datetime) -> bool:
    return session.status == SessionStatus.ACTIVE and session.starts_at <= now <= session.ends_at


async def start_verification(
    db: AsyncSession, student: Student, session_id: uuid.UUID
) -> AttendanceVerification:
    """docs/API.md §27: authenticated + enrolled + registered face +
    eligible for the session. Does not check for pre-existing attendance —
    there's no `attendance` table yet (Phase 5b), so that check belongs to
    the eventual `/complete` step, not here.
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
