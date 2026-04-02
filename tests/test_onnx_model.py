from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from src.infrastructure.onnx_model import ONNXModel


def _write_dummy_files(tmp_path: Path) -> tuple[Path, Path]:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = models_dir / "language_detector.onnx"
    classes_path = models_dir / "classes.json"

    onnx_path.write_bytes(b"dummy")
    classes_path.write_text(json.dumps(["en", "de"]), encoding="utf-8")
    return onnx_path, classes_path


class _DummyInput:
    def __init__(self, name: str) -> None:
        self.name = name


class _DummyOutput:
    def __init__(self, name: str) -> None:
        self.name = name


class _DummySession:
    def __init__(self, outputs: list[Any]) -> None:
        self._outputs = outputs

    def get_inputs(self) -> list[_DummyInput]:
        return [_DummyInput(name="input")]

    def get_outputs(self) -> list[_DummyOutput]:
        return [_DummyOutput(name="probabilities")]

    def run(self, output_names: list[str], feed: dict[str, Any]) -> list[Any]:
        _ = output_names
        _ = feed
        return self._outputs


def test_onnx_model_predict_validates_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    onnx_path, classes_path = _write_dummy_files(tmp_path)

    monkeypatch.setattr(
        "src.infrastructure.onnx_model.ort.InferenceSession",
        lambda *args, **kwargs: _DummySession(outputs=[np.array([[0.2, 0.8]], dtype=np.float32)]),
    )

    model = ONNXModel(onnx_path=onnx_path, classes_path=classes_path)
    assert model.predict(["hello"])[1] == ["en", "de"]

    with pytest.raises(ValueError, match="texts must be non-empty"):
        model.predict([])

    with pytest.raises(ValueError, match="all texts must be non-empty strings"):
        model.predict(["   "])


def test_onnx_model_predict_extracts_probabilities_ndarray(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    onnx_path, classes_path = _write_dummy_files(tmp_path)

    outputs = [np.array([[0.3, 0.7]], dtype=np.float32)]
    monkeypatch.setattr(
        "src.infrastructure.onnx_model.ort.InferenceSession",
        lambda *args, **kwargs: _DummySession(outputs=outputs),
    )

    model = ONNXModel(onnx_path=onnx_path, classes_path=classes_path)
    probabilities, labels = model.predict(["hello"])

    assert labels == ["en", "de"]
    assert probabilities[0][0] == pytest.approx(0.3)
    assert probabilities[0][1] == pytest.approx(0.7)


def test_onnx_model_extract_probabilities_zipmap_dict_branch() -> None:
    model: ONNXModel = object.__new__(ONNXModel)
    model._classes = ["en", "de"]  # type: ignore[attr-defined]

    outputs = [[{"en": 0.25, "de": 0.75}]]
    probs = model._extract_probabilities(outputs=outputs, output_names=["prob"], batch_size=1)

    assert probs == [[0.25, 0.75]]


def test_onnx_model_extract_probabilities_fallback_branch_by_output_name_length() -> None:
    model: ONNXModel = object.__new__(ONNXModel)
    model._classes = ["en", "de"]  # type: ignore[attr-defined]

    outputs = [
        np.array([0.1, 0.9], dtype=np.float32),
        np.array([[0.4, 0.6]], dtype=np.float32),
    ]
    probs = model._extract_probabilities(outputs=outputs, output_names=["only_one_name"], batch_size=1)

    assert probs[0][0] == pytest.approx(0.4)
    assert probs[0][1] == pytest.approx(0.6)


def test_onnx_model_extract_probabilities_raises_when_no_match() -> None:
    model: ONNXModel = object.__new__(ONNXModel)
    model._classes = ["en", "de"]  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="Unable to extract probabilities"):
        model._extract_probabilities(outputs=[[]], output_names=["prob"], batch_size=1)


def test_onnx_model_init_raises_on_missing_onnx_and_classes_and_empty_classes(
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    onnx_path_missing = models_dir / "language_detector.onnx"
    classes_path = models_dir / "classes.json"
    classes_path.write_text('["en","de"]', encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="ONNX model not found"):
        ONNXModel(onnx_path=onnx_path_missing, classes_path=classes_path)

    onnx_path = models_dir / "language_detector.onnx"
    onnx_path.write_bytes(b"dummy")
    classes_path_missing = models_dir / "classes.json"
    classes_path_missing.unlink(missing_ok=True)
    with pytest.raises(FileNotFoundError, match="classes.json not found"):
        ONNXModel(onnx_path=onnx_path, classes_path=classes_path_missing)

    classes_path_empty = models_dir / "classes.json"
    classes_path_empty.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty classes mapping"):
        ONNXModel(onnx_path=onnx_path, classes_path=classes_path_empty)

