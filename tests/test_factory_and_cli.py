import runpy
import sys
from typing import Any

import pytest

from src.application.services import ChurnAnalysisService, ChurnServiceConfig
from src.domain.entities import ChurnRisk, CustomerActivity
from src.domain.interfaces import IChurnModel
from src.infrastructure.churn_model import MockChurnModel
from src.presentation.factories import create_churn_analysis_service


class FixedRiskModel(IChurnModel):
    def __init__(self, risk: ChurnRisk) -> None:
        self._risk = risk

    def predict_risk(self, activity: CustomerActivity) -> ChurnRisk:
        return self._risk


class SuperCallingModel(IChurnModel):
    def predict_risk(self, activity: CustomerActivity) -> ChurnRisk:
        # Покрываем тело абстрактного метода интерфейса (raise NotImplementedError).
        return super().predict_risk(activity)


def test_factory_injects_model() -> None:
    fake_risk = ChurnRisk(is_high_risk=False, risk_score=0.3)
    service = create_churn_analysis_service(model=FixedRiskModel(fake_risk))

    risk = service.analyze(
        CustomerActivity(days_since_last_login=999, total_spend=1.0, support_tickets_count=999)
    )
    assert risk == fake_risk


def test_factory_passes_config() -> None:
    # Loyalty=10/(0+1)=10. При threshold=5 adjust не выполняется -> days=10 -> риск LOW.
    config = ChurnServiceConfig(loyalty_threshold=5.0)
    service = create_churn_analysis_service(model=MockChurnModel(), config=config)

    risk = service.analyze(
        CustomerActivity(days_since_last_login=10, total_spend=10.0, support_tickets_count=0)
    )
    assert risk.is_high_risk is False
    assert risk.risk_score == pytest.approx(0.2)


def test_interface_super_call_raises_not_implemented() -> None:
    model = SuperCallingModel()
    with pytest.raises(NotImplementedError):
        model.predict_risk(CustomerActivity(days_since_last_login=1, total_spend=1.0, support_tickets_count=1))


@pytest.mark.parametrize(
    "argv,expected_risk_label,expected_reco_lines",
    [
        (
            ["prog", "--client_id", "123", "--days_since_last_login", "40", "--total_spend", "200.0", "--support_tickets_count", "0"],
            "HIGH",
            ["- Offer discount", "- Contact support team"],
        ),
        (
            ["prog", "--client_id", "7", "--days_since_last_login", "10", "--total_spend", "100.0", "--support_tickets_count", "0"],
            "LOW",
            ["- Keep current service level"],
        ),
    ],
)
def test_cli_executes_and_prints_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str], expected_risk_label: str, expected_reco_lines: list[str]) -> None:  # noqa: E501
    monkeypatch.setattr(sys, "argv", argv)
    # Запускаем как main-модуль, чтобы покрыть ветку `if __name__ == "__main__"`.
    runpy.run_module("src.presentation.cli", run_name="__main__")

    out = capsys.readouterr().out
    assert "Client ID:" in out
    assert f"Risk: {expected_risk_label}" in out
    assert "Recommendation:" in out
    for line in expected_reco_lines:
        assert line in out

