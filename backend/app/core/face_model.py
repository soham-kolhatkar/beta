import logging

import numpy as np
from deepface import DeepFace
from deepface.modules.exceptions import FaceNotDetected

from app.core.config import settings
from app.core.errors import ApiError

logger = logging.getLogger("geoattend")


def warm_up() -> None:
    """Loads the face-recognition and face-detector models once at process
    startup so the first real request doesn't pay a ~5-45s cold-load cost
    (docs/SECURITY.md §67: load once at startup, reuse — never per request).
    """
    DeepFace.build_model(settings.face_model_name, task="facial_recognition")
    DeepFace.build_model(settings.face_detector_backend, task="face_detector")
    logger.info(
        "face_model_warmup model=%s detector=%s complete",
        settings.face_model_name,
        settings.face_detector_backend,
    )


def extract_embedding(image: np.ndarray) -> list[float]:
    """Detects the face in `image` (BGR numpy array) and returns its
    embedding. Raises ApiError with a docs/API.md §53 error code for
    anything that isn't a single, sufficiently confident face.
    """
    try:
        faces = DeepFace.represent(
            img_path=image,
            model_name=settings.face_model_name,
            detector_backend=settings.face_detector_backend,
            enforce_detection=True,
        )
    except FaceNotDetected as exc:
        raise ApiError(
            "FACE_NOT_DETECTED", "We couldn't detect a face in that image.", status_code=422
        ) from exc
    except ValueError as exc:
        # DeepFace also raises plain ValueError for other decode/processing
        # issues (corrupt data that passed our own pre-checks, etc.).
        raise ApiError(
            "FACE_PROCESSING_FAILED", "We couldn't process that image.", status_code=422
        ) from exc

    if len(faces) > 1:
        raise ApiError(
            "FACE_PROCESSING_FAILED",
            "Multiple faces were detected. Please submit a photo with only your face visible.",
            status_code=422,
        )

    face = faces[0]
    if face["face_confidence"] < settings.face_detection_min_confidence:
        raise ApiError(
            "FACE_PROCESSING_FAILED",
            "We couldn't get a clear enough view of your face. Try better lighting.",
            status_code=422,
        )

    return face["embedding"]
