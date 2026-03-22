"""
Реализация IDataStorage для MinIO и любого S3-совместимого API (boto3).
"""

from __future__ import annotations

from pathlib import Path

import boto3

from src.domain.interfaces import IDataStorage


class S3Storage(IDataStorage):
    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def download_file(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self._bucket, remote_path, str(local_path))

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        self._client.upload_file(str(local_path), self._bucket, remote_path)
