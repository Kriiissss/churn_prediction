from __future__ import annotations

from pathlib import Path

import pytest

import src.presentation.dependencies as deps
from src.application.services import InferenceService


class _DummyONNXModel:
    def __init__(self, *, onnx_path: Path, classes_path: Path) -> None:
        self.onnx_path = onnx_path
        self.classes_path = classes_path


class _FakeStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def download_file(self, remote_path: str, local_path: Path) -> None:
        self.calls.append((remote_path, local_path))
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"dummy")


def test_get_inference_service_uses_local_files_without_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / "language_detector.onnx").write_bytes(b"dummy")
    (models_dir / "classes.json").write_text('["en","de"]', encoding="utf-8")

    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()

    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    def _fail_create_s3_storage(*args: object, **kwargs: object) -> object:
        raise AssertionError("create_s3_storage should not be called when local model exists")

    monkeypatch.setattr(deps, "create_s3_storage", _fail_create_s3_storage)

    service = deps.get_inference_service()
    assert isinstance(service, InferenceService)
    assert isinstance(service._model, _DummyONNXModel)  # type: ignore[attr-defined]


def test_get_inference_service_downloads_when_missing_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()

    fake_storage = _FakeStorage()
    monkeypatch.setattr(deps, "create_s3_storage", lambda *args, **kwargs: fake_storage)
    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    monkeypatch.setenv("LANGUAGE_MODEL_ONNX_REMOTE_KEY", "remote/onnx/model.onnx")
    monkeypatch.setenv("LANGUAGE_MODEL_CLASSES_REMOTE_KEY", "remote/onnx/classes.json")

    service = deps.get_inference_service()
    assert isinstance(service, InferenceService)

    assert ("remote/onnx/model.onnx", tmp_path / "models" / "language_detector.onnx") in fake_storage.calls
    assert ("remote/onnx/classes.json", tmp_path / "models" / "classes.json") in fake_storage.calls


def test_get_inference_service_download_failure_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()

    class _FailStorage:
        def download_file(self, remote_path: str, local_path: Path) -> None:  # noqa: ARG002
            raise RuntimeError(f"download failed for {remote_path}")

    monkeypatch.setattr(deps, "create_s3_storage", lambda *args, **kwargs: _FailStorage())
    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    monkeypatch.setenv("LANGUAGE_MODEL_ONNX_REMOTE_KEY", "remote/onnx/model.onnx")
    monkeypatch.setenv("LANGUAGE_MODEL_CLASSES_REMOTE_KEY", "remote/onnx/classes.json")

    with pytest.raises(RuntimeError, match="Failed to download language model"):
        deps.get_inference_service()


def test_dependencies_repo_root_is_resolved_to_project_root() -> None:
    root = deps._repo_root()
    assert root.is_dir()

