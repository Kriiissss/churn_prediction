"""Покрытие абстрактного IDataStorage (аналогично IChurnModel)."""

from pathlib import Path

import pytest

from src.domain.interfaces import IDataStorage


class SuperCallingIDataStorage(IDataStorage):
    def download_file(self, remote_path: str, local_path: Path) -> None:
        return super().download_file(remote_path, local_path)

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        return super().upload_file(local_path, remote_path)


def test_idata_storage_super_calls_raise_not_implemented() -> None:
    storage = SuperCallingIDataStorage()
    with pytest.raises(NotImplementedError):
        storage.download_file("k", Path("x.txt"))
    with pytest.raises(NotImplementedError):
        storage.upload_file(Path("x.txt"), "k")
