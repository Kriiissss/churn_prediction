from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.domain.interfaces import IDataStorage


@dataclass(frozen=True, slots=True)
class DataSyncConfig:
    """Что синхронизировать: один объект в бакете ↔ локальный файл."""

    remote_key: str
    local_file: Path


class DataSyncService:
    """
    Use-case: при запуске убедиться, что локальный файл датасета существует.

    Если файла нет — скачать актуальную версию из хранилища (MinIO/S3).
    """

    def __init__(self, storage: IDataStorage, config: DataSyncConfig) -> None:
        self._storage = storage
        self._config = config

    def ensure_local(self) -> None:
        if self._config.local_file.exists():
            return
        self._storage.download_file(self._config.remote_key, self._config.local_file)
