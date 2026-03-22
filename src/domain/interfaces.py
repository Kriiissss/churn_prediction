from abc import ABC, abstractmethod
from pathlib import Path

from .entities import ChurnRisk, CustomerActivity


class IChurnModel(ABC):
    @abstractmethod
    def predict_risk(self, activity: CustomerActivity) -> ChurnRisk:
        raise NotImplementedError


class ILanguageDetector(ABC):
    """
    Определение языка текста по обучающему корпусу на диске.

    Список языков не фиксируется в коде: он выводится из структуры каталогов корпуса.
    """

    @abstractmethod
    def detect(self, text: str) -> str:
        """Возвращает код языка (имя подкаталога в корпусе), наиболее похожий на текст."""
        raise NotImplementedError

    @abstractmethod
    def get_available_languages(self) -> list[str]:
        """Коды языков, для которых в корпусе есть хотя бы один .txt файл."""
        raise NotImplementedError


class IDataStorage(ABC):
    """
    Абстракция объектного хранилища (S3-совместимый API, в т.ч. MinIO).

    remote_path — ключ объекта внутри бакета (без имени бакета).
    """

    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Скачать объект в локальный файл (создаёт родительские каталоги при необходимости)."""
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Загрузить локальный файл в объектное хранилище по ключу remote_path."""
        raise NotImplementedError

