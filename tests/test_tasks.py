from __future__ import annotations

from src.presentation import tasks


def test_detect_language_task_calls_inference_service(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeInference:
        def predict(self, text: str) -> tuple[str, float]:  # noqa: ARG002
            return "fr", 0.77

    monkeypatch.setattr(tasks, "get_inference_service", lambda: _FakeInference())
    result = tasks.detect_language_task("bonjour")
    assert result == {"language_code": "fr", "confidence": 0.77}
