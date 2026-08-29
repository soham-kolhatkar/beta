"""One-off model-evaluation spike for Phase 3 (docs/PLAN.md).

Evaluates candidate DeepFace backend models on accuracy (same-person vs.
different-person distance separation), embedding dimension, and per-call
latency on this machine's CPU, per the criteria docs/ARCHITECTURE.md §19
calls out (accuracy, speed, CPU/memory, deployment). This is NOT a
substitute for the real FAR/FRR threshold tuning docs/SECURITY.md §27
requires before production — that needs real classroom conditions and
volume neither available nor appropriate for a one-off script.

Usage: uv run python scripts/face_model_spike.py <path-to-3-test-images>
Expects <dir>/img1.jpg and img2.jpg to be the SAME person, img3.jpg a
DIFFERENT person (this matches the naming convention DeepFace's own test
fixtures use, e.g. https://github.com/serengil/deepface/tree/master/tests/unit/dataset).
"""

import sys
import time

from deepface import DeepFace

CANDIDATES = ["Facenet512", "ArcFace"]


# The "opencv" default detector backend needs haarcascade_frontalface_default.xml,
# which opencv-python 5.0.0 no longer bundles (a packaging regression, not a
# DeepFace issue). "retinaface" is more accurate than Haar cascades anyway and
# doesn't hit this.
DETECTOR_BACKEND = "retinaface"


def evaluate(model_name: str, img1: str, img2: str, img3: str) -> None:
    print(f"\n=== {model_name} ===")

    start = time.monotonic()
    embedding = DeepFace.represent(
        img_path=img1,
        model_name=model_name,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True,
    )[0]["embedding"]
    first_call_s = time.monotonic() - start
    print(f"embedding dimension: {len(embedding)}")
    print(f"first call latency (includes model load): {first_call_s:.2f}s")

    start = time.monotonic()
    DeepFace.represent(
        img_path=img2,
        model_name=model_name,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True,
    )
    warm_call_s = time.monotonic() - start
    print(f"warm call latency: {warm_call_s:.2f}s")

    same_person = DeepFace.verify(
        img1_path=img1,
        img2_path=img2,
        model_name=model_name,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True,
    )
    diff_person = DeepFace.verify(
        img1_path=img1,
        img2_path=img3,
        model_name=model_name,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True,
    )

    print(
        f"same-person distance:      {same_person['distance']:.4f} "
        f"(threshold {same_person['threshold']:.4f}, verified={same_person['verified']})"
    )
    print(
        f"different-person distance: {diff_person['distance']:.4f} "
        f"(threshold {diff_person['threshold']:.4f}, verified={diff_person['verified']})"
    )


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <dir-with-img1.jpg-img2.jpg-img3.jpg>")
        sys.exit(1)

    directory = sys.argv[1].rstrip("/")
    img1, img2, img3 = f"{directory}/img1.jpg", f"{directory}/img2.jpg", f"{directory}/img3.jpg"

    for model_name in CANDIDATES:
        evaluate(model_name, img1, img2, img3)


if __name__ == "__main__":
    main()
