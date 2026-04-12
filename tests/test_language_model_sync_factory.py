from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.infrastructure.storage_settings import StorageSettings
from src.presentation.factories import create_language_model_sync_service


def test_create_language_model_sync_service_builds_multi_config(tmp_path: Path) -> None:
    storage = MagicMock()
    settings = StorageSettings(
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
        bucket="datasets",
        models_bucket="models",
        language_model_onnx_remote_key="language_detector.onnx",
        language_model_classes_remote_key="classes.json",
        language_model_onnx_local_file=tmp_path / "models" / "language_detector.onnx",
        language_model_classes_local_file=tmp_path / "models" / "classes.json",
        data_sync_remote_key="ignored",
        data_sync_local_file=tmp_path / "ignored.txt",
    )

    svc = create_language_model_sync_service(storage=storage, settings=settings)
    assert svc._config.items is not None  # type: ignore[attr-defined]
    assert svc._config.items[0] == ("language_detector.onnx", settings.language_model_onnx_local_file)
    assert svc._config.items[1] == ("classes.json", settings.language_model_classes_local_file)
