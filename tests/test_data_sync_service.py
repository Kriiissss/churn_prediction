from __future__ import annotations

from pathlib import Path

from src.application.data_sync_service import DataSyncConfig, DataSyncService
from src.domain.interfaces import IDataStorage


class RecordingStorage(IDataStorage):
    def __init__(self) -> None:
        self.download_calls: list[tuple[str, Path]] = []
        self.upload_calls: list[tuple[Path, str]] = []

    def download_file(self, remote_path: str, local_path: Path) -> None:
        self.download_calls.append((remote_path, local_path))

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        self.upload_calls.append((local_path, remote_path))


def test_data_sync_skips_when_file_exists(tmp_path: Path) -> None:
    local = tmp_path / "a.txt"
    local.write_text("x", encoding="utf-8")
    storage = RecordingStorage()
    cfg = DataSyncConfig(remote_key="k", local_file=local)
    DataSyncService(storage, cfg).ensure_local()
    assert storage.download_calls == []


def test_data_sync_downloads_when_missing(tmp_path: Path) -> None:
    local = tmp_path / "missing" / "a.txt"
    storage = RecordingStorage()
    cfg = DataSyncConfig(remote_key="remote/k.txt", local_file=local)
    DataSyncService(storage, cfg).ensure_local()
    assert storage.download_calls == [("remote/k.txt", local)]
