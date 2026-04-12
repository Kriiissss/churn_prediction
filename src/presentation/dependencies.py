from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from src.application.services import InferenceService
from src.infrastructure.onnx_model import ONNXModel


def _repo_root() -> Path:
    # src/presentation/dependencies.py -> parents[2] == корень репозитория
    return Path(__file__).resolve().parents[2]


def _dvc_pull_language_model_artifacts(repo: Path) -> None:
    """
    Подтягивает ONNX + classes.json из DVC remote `models_storage`.

    В MinIO объекты лежат под префиксом из URL remote (`…/dvc-store/...`), а не как
    отдельные ключи `language_detector.onnx` в корне бакета — поэтому здесь DVC, а не S3 GET по имени файла.
    """
    models = repo / "models"
    onnx_dvc = models / "language_detector.onnx.dvc"
    classes_dvc = models / "classes.json.dvc"
    if not onnx_dvc.is_file() or not classes_dvc.is_file():
        raise RuntimeError(
            "DVC metadata for the language model is missing (expected "
            f"{onnx_dvc.name} and {classes_dvc.name} under {models}). "
            "Train and push first: `poetry run python scripts/train_model.py ...` "
            "(without --skip-dvc), and keep the generated *.dvc files in the project."
        )
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "dvc",
            "pull",
            "-r",
            "models_storage",
            "models/language_detector.onnx.dvc",
            "models/classes.json.dvc",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600.0,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(
            "dvc pull for language model failed.\n"
            f"stdout:\n{out.stdout}\n"
            f"stderr:\n{out.stderr}\n"
            "Hint: MinIO running (`docker compose up -d`), remote `models_storage` in `.dvc/config`, "
            "and credentials in `.dvc/config.local` (see README)."
        )


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
        try:
            _dvc_pull_language_model_artifacts(repo)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Failed to restore language model artifacts via DVC. "
                "Ensure MinIO is running, `models_storage` is configured, and the model was pushed after training. "
                f"Original error: {e}"
            ) from e

    model = ONNXModel(onnx_path=onnx_path, classes_path=classes_path)
    return InferenceService(model=model)

