from __future__ import annotations

from fastapi.testclient import TestClient

import src.presentation.api as api


class _FakeInferenceService:
    def predict(self, text: str) -> tuple[str, float]:  # noqa: ARG002
        return "de", 0.97


def test_detect_language_endpoint_returns_expected_response() -> None:
    api.app.dependency_overrides[api.get_inference_service] = lambda: _FakeInferenceService()
    try:
        client = TestClient(api.app)
        resp = client.post(
            "/api/v1/text/detect_language",
            json={"text": "Hallo Welt"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["language_code"] == "de"
        assert data["confidence"] == 0.97
    finally:
        api.app.dependency_overrides.clear()

