from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import src.presentation.dependencies as deps
from src.application.services import InferenceService


class _DummyONNXModel:
    def __init__(self, *, onnx_path: Path, classes_path: Path) -> None:
        self.onnx_path = onnx_path
        self.classes_path = classes_path


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

    def _fail_dvc_pull(*args: object, **kwargs: object) -> None:
        raise AssertionError("dvc pull should not run when local model exists")

    monkeypatch.setattr(deps, "_dvc_pull_language_model_artifacts", _fail_dvc_pull)

    service = deps.get_inference_service()
    assert isinstance(service, InferenceService)
    assert isinstance(service._model, _DummyONNXModel)  # type: ignore[attr-defined]


def test_get_inference_service_pulls_via_dvc_when_missing_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()

    pulls = {"n": 0}

    def _fake_pull(repo: Path) -> None:
        pulls["n"] += 1
        models_dir = repo / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / "language_detector.onnx").write_bytes(b"dummy")
        (models_dir / "classes.json").write_text('["en","de"]', encoding="utf-8")

    monkeypatch.setattr(deps, "_dvc_pull_language_model_artifacts", _fake_pull)
    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    service = deps.get_inference_service()
    assert isinstance(service, InferenceService)

    assert pulls["n"] == 1


def test_get_inference_service_download_failure_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()

    def _fail_pull(_repo: Path) -> None:
        raise RuntimeError("dvc pull failed")

    monkeypatch.setattr(deps, "_dvc_pull_language_model_artifacts", _fail_pull)
    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    with pytest.raises(RuntimeError, match="Failed to restore language model artifacts via DVC"):
        deps.get_inference_service()


def test_get_inference_service_raises_when_dvc_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(deps, "_repo_root", lambda: tmp_path)
    deps.get_inference_service.cache_clear()
    (tmp_path / "models").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(deps, "ONNXModel", _DummyONNXModel)

    with pytest.raises(RuntimeError, match="Failed to restore language model artifacts via DVC"):
        deps.get_inference_service()


def test_dependencies_repo_root_is_resolved_to_project_root() -> None:
    root = deps._repo_root()
    assert root.is_dir()


def test_dvc_pull_language_model_raises_when_dvc_files_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="DVC metadata for the language model is missing"):
        deps._dvc_pull_language_model_artifacts(tmp_path)


def test_dvc_pull_language_model_runs_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir(parents=True, exist_ok=True)
    (models / "language_detector.onnx.dvc").write_text("outs: []\n", encoding="utf-8")
    (models / "classes.json.dvc").write_text("outs: []\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run(cmd: object, **kwargs: object) -> SimpleNamespace:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(deps.subprocess, "run", _fake_run)
    deps._dvc_pull_language_model_artifacts(tmp_path)
    cmd = captured["cmd"]
    assert isinstance(cmd, (list, tuple))
    assert "models_storage" in cmd
    assert captured["kwargs"].get("cwd") == tmp_path


def test_dvc_pull_language_model_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir(parents=True, exist_ok=True)
    (models / "language_detector.onnx.dvc").write_text("x", encoding="utf-8")
    (models / "classes.json.dvc").write_text("x", encoding="utf-8")

    def _fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="out", stderr="err")

    monkeypatch.setattr(deps.subprocess, "run", _fake_run)
    with pytest.raises(RuntimeError, match="dvc pull for language model failed"):
        deps._dvc_pull_language_model_artifacts(tmp_path)

