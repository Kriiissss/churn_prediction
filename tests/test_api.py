from __future__ import annotations

from fastapi.testclient import TestClient

import src.presentation.api as api


def test_detect_language_async_returns_task_id(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeTask:
        id = "task-123"

    class _FakeDetectTask:
        @staticmethod
        def delay(text: str) -> _FakeTask:  # noqa: ARG004
            return _FakeTask()

    monkeypatch.setattr(api, "detect_language_task", _FakeDetectTask())
    client = TestClient(api.app)
    resp = client.post("/api/v1/text/detect_language_async", json={"text": "Hallo Welt"})
    assert resp.status_code == 202
    assert resp.json() == {"task_id": "task-123"}


def test_get_language_result_pending(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeAsyncResult:
        def __init__(self, task_id: str, app) -> None:  # noqa: ANN001
            self.task_id = task_id
            self.status = "PENDING"

        def ready(self) -> bool:
            return False

    monkeypatch.setattr(api, "AsyncResult", _FakeAsyncResult)
    client = TestClient(api.app)
    resp = client.get("/api/v1/text/results/task-123")
    assert resp.status_code == 200
    assert resp.json() == {"task_id": "task-123", "status": "PENDING", "result": None}


def test_get_language_result_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeAsyncResult:
        def __init__(self, task_id: str, app) -> None:  # noqa: ANN001
            self.task_id = task_id
            self.status = "SUCCESS"

        def ready(self) -> bool:
            return True

        def get(self):  # noqa: ANN201
            return {"language_code": "de", "confidence": 0.88}

    monkeypatch.setattr(api, "AsyncResult", _FakeAsyncResult)
    client = TestClient(api.app)
    resp = client.get("/api/v1/text/results/task-123")
    assert resp.status_code == 200
    assert resp.json() == {
        "task_id": "task-123",
        "status": "SUCCESS",
        "result": {"language_code": "de", "confidence": 0.88},
    }


def test_get_language_result_success_with_non_dict_payload(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeAsyncResult:
        def __init__(self, task_id: str, app) -> None:  # noqa: ANN001
            self.task_id = task_id
            self.status = "SUCCESS"

        def ready(self) -> bool:
            return True

        def get(self):  # noqa: ANN201
            return "done"

    monkeypatch.setattr(api, "AsyncResult", _FakeAsyncResult)
    client = TestClient(api.app)
    resp = client.get("/api/v1/text/results/task-123")
    assert resp.status_code == 200
    assert resp.json() == {
        "task_id": "task-123",
        "status": "SUCCESS",
        "result": {"raw_result": "done"},
    }


def test_get_language_result_failure_returns_error_payload(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _FakeAsyncResult:
        def __init__(self, task_id: str, app) -> None:  # noqa: ANN001
            self.task_id = task_id
            self.status = "FAILURE"
            self.result = RuntimeError("boom")

        def failed(self) -> bool:
            return True

        def ready(self) -> bool:
            return True

        def get(self):  # noqa: ANN201
            raise AssertionError("get() should not be called for FAILURE")

    monkeypatch.setattr(api, "AsyncResult", _FakeAsyncResult)
    client = TestClient(api.app)
    resp = client.get("/api/v1/text/results/task-123")
    assert resp.status_code == 200
    assert resp.json() == {
        "task_id": "task-123",
        "status": "FAILURE",
        "result": {"error": "boom"},
    }

