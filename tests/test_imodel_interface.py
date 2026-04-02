from __future__ import annotations

import pytest

from src.domain.interfaces import IModel


class SuperCallingModel(IModel):
    def predict(self, texts: list[str]):  # type: ignore[override]
        return super().predict(texts)


def test_imodel_interface_super_call_raises_not_implemented() -> None:
    model = SuperCallingModel()
    with pytest.raises(NotImplementedError):
        model.predict(["hello"])

