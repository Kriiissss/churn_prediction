from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.domain.interfaces import IDataStorage


@dataclass(frozen=True, slots=True)
class DataSyncConfig:
    """
    Что синхронизировать.

    Поддерживаются два режима:
    - legacy: один объект `remote_key` ↔ `local_file`
    - multi: несколько объектов через `items`
    """

    remote_key: str | None = None
    local_file: Path | None = None
    items: tuple[tuple[str, Path], ...] | None = None


class DataSyncService:
    """
    Use-case: при запуске убедиться, что локальный файл датасета существует.

    Если файла нет — скачать актуальную версию из хранилища (MinIO/S3).
    """

    def __init__(self, storage: IDataStorage, config: DataSyncConfig) -> None:
        self._storage = storage
        self._config = config

    def ensure_local(self) -> None:
        if self._config.items is not None:
            for remote_key, local_file in self._config.items:
                if local_file.exists():
                    continue
                self._storage.download_file(remote_key, local_file)
            return

        if self._config.local_file is None or self._config.remote_key is None:
            raise ValueError("DataSyncConfig: укажите либо items, либо пару remote_key/local_file")

        if self._config.local_file.exists():
            return
        self._storage.download_file(self._config.remote_key, self._config.local_file)
