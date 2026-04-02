from __future__ import annotations

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from src.application.services import InferenceService
from src.presentation.dependencies import get_inference_service


app = FastAPI(title="Churn Prediction + Language Detection (FastAPI)")


class DetectLanguageRequest(BaseModel):
    text: str = Field(min_length=1, description="Текст для определения языка")


class DetectLanguageResponse(BaseModel):
    language_code: str
    confidence: float


@app.post(
    "/api/v1/text/detect_language",
    response_model=DetectLanguageResponse,
)
def detect_language(
    payload: DetectLanguageRequest,
    service: InferenceService = Depends(get_inference_service),
) -> DetectLanguageResponse:
    language_code, confidence = service.predict(payload.text)
    return DetectLanguageResponse(language_code=language_code, confidence=confidence)

