from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Values the docs deliberately leave unfixed
    (GPS accuracy cutoff, face similarity threshold, verification TTL, etc.)
    live here as named settings, never as inline magic numbers, so each can
    be tuned when the phase that needs it is implemented.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://geoattend:geoattend@localhost:5432/geoattend"

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    # Phase 1: session cookie settings. The session token itself is a random
    # opaque value verified against the `sessions` table (see core/security.py),
    # so no signing secret is needed here.
    session_cookie_name: str = "geoattend_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days

    # Phase 7: Arcjet.
    arcjet_key: str = ""

    # Phase 3/5b: face model + verification thresholds. Chosen via the
    # scripts/face_model_spike.py evaluation (see PROGRESS.md) — Facenet512
    # showed much cleaner same/different-person separation than ArcFace on
    # that (small, non-rigorous) spike. Threshold is DeepFace's own
    # calibrated default for Facenet512+cosine, not yet validated against
    # real classroom conditions (docs/SECURITY.md §27 requires that before
    # production).
    face_model_name: str = "Facenet512"
    face_embedding_dimension: int = 512
    # "opencv" (DeepFace's default detector) needs a haarcascade file that
    # opencv-python 5.x no longer bundles in this environment; retinaface
    # sidesteps that and is more accurate anyway.
    face_detector_backend: str = "retinaface"
    face_similarity_threshold: float = 0.30
    face_detection_min_confidence: float = 0.90
    face_upload_max_bytes: int = 5 * 1024 * 1024
    face_min_image_dimension_px: int = 200

    # Phase 5a: location + verification-context settings.
    # `accuracy_meters` (as reported by the browser Geolocation API) is a
    # radius of uncertainty, not a floor — reject readings above this, per
    # docs/SECURITY.md §21's "distance=30m, accuracy=±500m is unreliable"
    # example. 50m tolerates weak/indoor signal while catching genuinely bad
    # readings; not yet validated against real classroom conditions (same
    # caveat as the face similarity threshold).
    location_max_accuracy_meters: float = 50.0
    # Short-lived on purpose (docs/API.md §35) — long enough to walk through
    # location + face verification in one sitting, short enough to limit
    # replay/reuse of a context.
    verification_context_ttl_seconds: int = 120

    # Phase 4: attendance session radius bounds. Below the min, ordinary GPS
    # accuracy (~5-20m on a phone) would cause false LOCATION_OUTSIDE_RADIUS
    # rejections for legitimately-present students; above the max, the
    # geofence stops meaningfully constraining who can mark attendance.
    session_min_radius_meters: float = 10.0
    session_max_radius_meters: float = 500.0


settings = Settings()
