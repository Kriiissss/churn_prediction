from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from src.application.services import InferenceService
from src.infrastructure.onnx_model import ONNXModel
from src.presentation.factories import create_s3_storage


def _repo_root() -> Path:
    # src/presentation/dependencies.py -> parents[2] == корень репозитория
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_inference_service() -> InferenceService:
    """
    FastAPI dependency:
      - поднимает ONNXModel
      - при отсутствии моделей скачивает их из MinIO (S3-совместимое хранилище)
    """
    repo = _repo_root()
    models_dir = repo / "models"
    onnx_path = models_dir / "language_detector.onnx"
    classes_path = models_dir / "classes.json"

    if not onnx_path.is_file() or not classes_path.is_file():
        models_dir.mkdir(parents=True, exist_ok=True)

        remote_onnx_key = os.getenv(
            "LANGUAGE_MODEL_ONNX_REMOTE_KEY",
            "language_detector.onnx",
        )
        remote_classes_key = os.getenv(
            "LANGUAGE_MODEL_CLASSES_REMOTE_KEY",
            "classes.json",
        )

        models_bucket = os.getenv("MINIO_MODELS_BUCKET", "models")
        storage = create_s3_storage(bucket_override=models_bucket)
        try:
            if not onnx_path.is_file():
                storage.download_file(remote_onnx_key, onnx_path)
            if not classes_path.is_file():
                storage.download_file(remote_classes_key, classes_path)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Failed to download language model from MinIO/S3. "
                f"Check bucket/credentials and remote keys: {remote_onnx_key}, {remote_classes_key}. "
                f"Original error: {e}"
            ) from e

    model = ONNXModel(onnx_path=onnx_path, classes_path=classes_path)
    return InferenceService(model=model)

