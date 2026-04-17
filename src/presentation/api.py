from __future__ import annotations

from celery.result import AsyncResult
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.presentation.celery_app import celery_app
from src.presentation.tasks import detect_language_task


app = FastAPI(title="Churn Prediction + Language Detection (FastAPI)")


class DetectLanguageRequest(BaseModel):
    text: str = Field(min_length=1, description="Текст для определения языка")


class AsyncTaskResponse(BaseModel):
    task_id: str


class AsyncResultResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, float | str] | None = None


@app.post(
    "/api/v1/text/detect_language_async",
    response_model=AsyncTaskResponse,
    status_code=202,
)
def detect_language_async(payload: DetectLanguageRequest) -> AsyncTaskResponse:
    task = detect_language_task.delay(payload.text)
    return AsyncTaskResponse(task_id=task.id)


@app.get(
    "/api/v1/text/results/{task_id}",
    response_model=AsyncResultResponse,
)
def get_language_result(task_id: str) -> AsyncResultResponse:
    task_result = AsyncResult(task_id, app=celery_app)
    is_failed = getattr(task_result, "failed", lambda: task_result.status == "FAILURE")()
    if is_failed:
        return AsyncResultResponse(
            task_id=task_id,
            status=task_result.status,
            result={"error": str(task_result.result)},
        )
    if task_result.ready():
        result = task_result.get()
        if not isinstance(result, dict):
            result = {"raw_result": str(result)}
        return AsyncResultResponse(
            task_id=task_id,
            status=task_result.status,
            result=result,
        )
    return AsyncResultResponse(task_id=task_id, status=task_result.status)

