from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.infrastructure.storage_settings import StorageSettings, load_storage_settings


def test_load_storage_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # Не читаем реальный .env: иначе значения из файла перебьют ожидаемые дефолты.
    monkeypatch.setattr("src.infrastructure.storage_settings.load_dotenv", lambda **kwargs: None)
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)

    s = load_storage_settings()
    assert s.endpoint_url == "http://localhost:9000"
    assert s.access_key == "minioadmin"
    assert s.secret_key == "minioadmin"
    assert s.bucket == "datasets"
    assert s.data_sync_remote_key == "lab/corpus/en/sample_01.txt"
    assert s.data_sync_local_file.name == "sample_01.txt"


def test_storage_settings_frozen_dataclass() -> None:
    s = StorageSettings(
        endpoint_url="http://x",
        access_key="a",
        secret_key="s",
        bucket="b",
        data_sync_remote_key="k",
        data_sync_local_file=Path("p"),
    )
    with pytest.raises(FrozenInstanceError):
        s.bucket = "no"  # type: ignore[misc]
