from __future__ import annotations

from pathlib import Path

from src.application.data_sync_service import DataSyncConfig, DataSyncService
from src.application.services import ChurnAnalysisService, ChurnServiceConfig
from src.domain.interfaces import IChurnModel, IDataStorage, ILanguageDetector
from src.infrastructure.churn_model import MockChurnModel
from src.infrastructure.language_detector import CorpusLanguageDetector
from src.infrastructure.storage_settings import StorageSettings, load_storage_settings


def create_churn_analysis_service(
    *,
    model: IChurnModel | None = None,
    config: ChurnServiceConfig | None = None,
) -> ChurnAnalysisService:
    """
    Фабрика сборки сервиса (composition root в внешнем слое).

    Application/Domain остаются независимыми: здесь связываются интерфейсы и реализации.
    """

    resolved_model = model or MockChurnModel()
    resolved_config = config
    return ChurnAnalysisService(model=resolved_model, config=resolved_config)


def create_language_detector(
    *,
    corpus_root: Path | None = None,
) -> ILanguageDetector:
    """Сборка детектора языка: корпус на диске, языки из структуры каталогов."""
    return CorpusLanguageDetector(corpus_root=corpus_root)


def create_s3_storage(
    settings: StorageSettings | None = None,
) -> IDataStorage:
    """S3/MinIO-хранилище из настроек окружения (.env)."""
    # Ленивый импорт: boto3 нужен только для сценариев с объектным хранилищем.
    from src.infrastructure.s3_storage import S3Storage

    resolved = settings or load_storage_settings()
    return S3Storage(
        bucket=resolved.bucket,
        endpoint_url=resolved.endpoint_url,
        access_key=resolved.access_key,
        secret_key=resolved.secret_key,
    )


def create_data_sync_service(
    *,
    storage: IDataStorage | None = None,
    config: DataSyncConfig | None = None,
    settings: StorageSettings | None = None,
) -> DataSyncService:
    """Синхронизация демо-файла корпуса: локально или из MinIO."""
    resolved_settings = settings or load_storage_settings()
    resolved_storage = storage or create_s3_storage(resolved_settings)
    resolved_config = config or DataSyncConfig(
        remote_key=resolved_settings.data_sync_remote_key,
        local_file=resolved_settings.data_sync_local_file,
    )
    return DataSyncService(storage=resolved_storage, config=resolved_config)

