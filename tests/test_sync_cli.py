import runpy
import sys

import pytest


def test_sync_cli_main_invokes_ensure_local(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"n": 0}

    class _FakeService:
        def ensure_local(self) -> None:
            called["n"] += 1

    import src.presentation.sync_cli as sync_cli

    monkeypatch.setattr(sync_cli, "create_data_sync_service", lambda: _FakeService())
    sync_cli.main()
    assert called["n"] == 1


def test_sync_cli_main_guard_runs_when_executed_as___main__(monkeypatch: pytest.MonkeyPatch) -> None:
    """Покрывает ветку if __name__ == '__main__' при «чистом» импорте модуля."""
    called = {"n": 0}

    class _FakeService:
        def ensure_local(self) -> None:
            called["n"] += 1

    monkeypatch.setattr(
        "src.presentation.factories.create_data_sync_service",
        lambda: _FakeService(),
    )
    sys.modules.pop("src.presentation.sync_cli", None)
    runpy.run_module("src.presentation.sync_cli", run_name="__main__")
    assert called["n"] == 1
