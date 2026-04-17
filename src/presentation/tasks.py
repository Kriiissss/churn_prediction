from __future__ import annotations

from src.presentation.celery_app import celery_app
from src.presentation.dependencies import get_inference_service


@celery_app.task(name="detect_language")
def detect_language_task(text: str) -> dict[str, float | str]:
    inference_service = get_inference_service()
    language_code, confidence = inference_service.predict(text)
    return {
        "language_code": language_code,
        "confidence": confidence,
    }
