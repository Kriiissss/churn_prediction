"""
Параметры подключения к MinIO/S3 из переменных окружения и .env (без секретов в коде).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _repo_root() -> Path:
    # src/infrastructure/storage_settings.py -> parents[2] == корень репозитория
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class StorageSettings:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str
    data_sync_remote_key: str
    data_sync_local_file: Path


def load_storage_settings() -> StorageSettings:
    """
    Читает .env (если есть) и переменные окружения.

    Значения по умолчанию совпадают с docker-compose.yml (MinIO).
    """
    load_dotenv(dotenv_path=_repo_root() / ".env")
    default_local = _repo_root() / "data" / "corpus" / "en" / "sample_01.txt"
    # Пути для DataSyncService (sync_cli) не выносятся в .env — только константы проекта.
    return StorageSettings(
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        bucket=os.getenv("MINIO_BUCKET", "datasets"),
        data_sync_remote_key="lab/corpus/en/sample_01.txt",
        data_sync_local_file=default_local,
    )
