"""
CLI: при необходимости скачать демо-файл корпуса из MinIO (DataSyncService).
"""

from __future__ import annotations

from src.presentation.factories import create_data_sync_service


def main() -> None:
    service = create_data_sync_service()
    service.ensure_local()


if __name__ == "__main__":
    main()
