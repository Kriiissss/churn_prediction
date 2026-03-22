from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.infrastructure.s3_storage import S3Storage


def test_s3_storage_download_and_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()

    def _fake_client(*args: object, **kwargs: object) -> MagicMock:
        return mock_client

    monkeypatch.setattr("src.infrastructure.s3_storage.boto3.client", _fake_client)

    storage = S3Storage(
        bucket="datasets",
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="s",
    )

    local = tmp_path / "nested" / "f.txt"
    storage.download_file("remote/key.txt", local)

    mock_client.download_file.assert_called_once_with("datasets", "remote/key.txt", str(local))

    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("hi", encoding="utf-8")
    storage.upload_file(local, "out/key.txt")

    mock_client.upload_file.assert_called_once_with(str(local), "datasets", "out/key.txt")
