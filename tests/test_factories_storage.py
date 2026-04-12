from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.data_sync_service import DataSyncConfig
from src.infrastructure.storage_settings import StorageSettings
from src.presentation.factories import create_data_sync_service, create_s3_storage


def test_create_s3_storage_builds_client(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()

    def _fake_client(*args: object, **kwargs: object) -> MagicMock:
        return mock_client

    monkeypatch.setattr("src.infrastructure.s3_storage.boto3.client", _fake_client)

    settings = StorageSettings(
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
        bucket="datasets",
        models_bucket="models",
        language_model_onnx_remote_key="language_detector.onnx",
        language_model_classes_remote_key="classes.json",
        language_model_onnx_local_file=Path("models/language_detector.onnx"),
        language_model_classes_local_file=Path("models/classes.json"),
        data_sync_remote_key="k",
        data_sync_local_file=Path("x"),
    )
    storage = create_s3_storage(settings)
    storage.download_file("rk", Path("/tmp/x.txt"))
    mock_client.download_file.assert_called()


def test_create_data_sync_service_with_explicit_deps(tmp_path: Path) -> None:
    storage = MagicMock()
    local = tmp_path / "f.txt"
    cfg = DataSyncConfig(remote_key="rk", local_file=local)
    svc = create_data_sync_service(storage=storage, config=cfg, settings=_dummy_settings(local))
    svc.ensure_local()
    storage.download_file.assert_called_once_with("rk", local)


def _dummy_settings(local: Path) -> StorageSettings:
    return StorageSettings(
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
        bucket="b",
        models_bucket="models",
        language_model_onnx_remote_key="language_detector.onnx",
        language_model_classes_remote_key="classes.json",
        language_model_onnx_local_file=Path("models/language_detector.onnx"),
        language_model_classes_local_file=Path("models/classes.json"),
        data_sync_remote_key="ignored",
        data_sync_local_file=local,
    )


def test_create_s3_storage_loads_settings_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_boto_client = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("src.infrastructure.s3_storage.boto3.client", fake_boto_client)
    fake = StorageSettings(
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
        bucket="datasets",
        models_bucket="models",
        language_model_onnx_remote_key="language_detector.onnx",
        language_model_classes_remote_key="classes.json",
        language_model_onnx_local_file=tmp_path / "models" / "language_detector.onnx",
        language_model_classes_local_file=tmp_path / "models" / "classes.json",
        data_sync_remote_key="k",
        data_sync_local_file=tmp_path / "x.txt",
    )
    monkeypatch.setattr("src.presentation.factories.load_storage_settings", lambda: fake)

    create_s3_storage()
    fake_boto_client.assert_called_once()


def test_create_data_sync_service_without_explicit_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mock_client = MagicMock()

    def _fake_client(*args: object, **kwargs: object) -> MagicMock:
        return mock_client

    monkeypatch.setattr("src.infrastructure.s3_storage.boto3.client", _fake_client)
    fake = StorageSettings(
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
        bucket="datasets",
        models_bucket="models",
        language_model_onnx_remote_key="language_detector.onnx",
        language_model_classes_remote_key="classes.json",
        language_model_onnx_local_file=tmp_path / "models" / "language_detector.onnx",
        language_model_classes_local_file=tmp_path / "models" / "classes.json",
        data_sync_remote_key="rk",
        data_sync_local_file=tmp_path / "missing.txt",
    )
    monkeypatch.setattr("src.presentation.factories.load_storage_settings", lambda: fake)

    svc = create_data_sync_service()
    svc.ensure_local()

    mock_client.download_file.assert_called_once()
