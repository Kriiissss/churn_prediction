from __future__ import annotations

import pytest

from src.application.services import InferenceService
from src.domain.interfaces import IModel


class FixedModel(IModel):
    def predict(self, texts: list[str]):  # type: ignore[override]
        return [[0.1, 0.9]], ["en", "de"]


def test_inference_service_predict_returns_best_label_and_confidence() -> None:
    service = InferenceService(model=FixedModel())
    language_code, confidence = service.predict("Hallo Welt")
    assert language_code == "de"
    assert confidence == pytest.approx(0.9)


def test_inference_service_lowercases_input_before_model() -> None:
    captured: dict[str, list[str]] = {}

    class _CaptureModel(IModel):
        def predict(self, texts: list[str]):  # type: ignore[override]
            captured["texts"] = texts
            return [[1.0]], ["en"]

    service = InferenceService(model=_CaptureModel())
    service.predict("HaLLo")
    assert captured["texts"] == ["hallo"]

