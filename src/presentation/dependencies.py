from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from src.application.services import InferenceService
from src.infrastructure.onnx_model import ONNXModel

MLFLOW_ONNX_ARTIFACT_PATH = "language_model_onnx"
MLFLOW_META_ARTIFACT_PATH = "language_model_artifacts"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sync_from_mlflow_registry(models_dir: Path) -> bool:
    uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
    if not uri:
        return False

    model_name = os.getenv("MLFLOW_MODEL_NAME", "language_detector")
    model_stage = os.getenv("MLFLOW_MODEL_STAGE", "Production")
    try:
        import mlflow
        from mlflow.artifacts import download_artifacts
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri(uri)
        client = MlflowClient()
        versions = client.get_latest_versions(model_name, stages=[model_stage])
        if not versions:
            return False

        # Берем самую новую версию в нужной стадии.
        latest = sorted(versions, key=lambda mv: int(getattr(mv, "version", "0")), reverse=True)[0]
        run_id = getattr(latest, "run_id", None)
        if not run_id:
            return False

        onnx_uri = f"runs:/{run_id}/{MLFLOW_ONNX_ARTIFACT_PATH}/model.onnx"
        classes_uri = f"runs:/{run_id}/{MLFLOW_META_ARTIFACT_PATH}/classes.json"
        models_dir.mkdir(parents=True, exist_ok=True)

        onnx_tmp = download_artifacts(onnx_uri, dst_path=str(models_dir))
        classes_tmp = download_artifacts(classes_uri, dst_path=str(models_dir))
        Path(onnx_tmp).replace(models_dir / "language_detector.onnx")
        Path(classes_tmp).replace(models_dir / "classes.json")
        (models_dir / "mlflow_model_info.json").write_text(
            json.dumps(
                {
                    "model_name": model_name,
                    "stage": model_stage,
                    "version": str(getattr(latest, "version", "")),
                    "run_id": run_id,
                    "tracking_uri": uri,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def get_inference_service() -> InferenceService:
    """
    Worker dependency:
      - поднимает ONNXModel
      - при старте синхронизирует последнюю модель из MLflow Model Registry.
    """
    repo = _repo_root()
    models_dir = repo / "models"
    onnx_path = models_dir / "language_detector.onnx"
    classes_path = models_dir / "classes.json"

    models_dir.mkdir(parents=True, exist_ok=True)
    pulled = _sync_from_mlflow_registry(models_dir)
    if not pulled:
        raise RuntimeError(
            "Failed to restore language model artifacts from MLflow Registry. "
            "Set MLFLOW_TRACKING_URI and ensure a Production version exists for MLFLOW_MODEL_NAME."
        )

    model = ONNXModel(onnx_path=onnx_path, classes_path=classes_path)
    return InferenceService(model=model)

