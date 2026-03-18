import pytest

from src.application.services import ChurnAnalysisService, ChurnServiceConfig
from src.domain.entities import CustomerActivity
from src.infrastructure.churn_model import MockChurnModel


@pytest.mark.parametrize(
    "days_since_last_login,total_spend,support_tickets_count,expected_is_high,expected_score",
    [
        (40, 200.0, 0, True, 0.8),  # already high by days
        (10, 10.0, 0, True, 0.8),  # low loyalty -> adjust -> high
        (10, 100.0, 0, False, 0.2),  # high loyalty -> stays low
        (20, 100.0, 6, True, 0.8),  # high by tickets
        (-30, 10.0, 0, False, 0.2),  # negative days -> clamp to 0 on adjust
    ],
)
def test_churn_analysis_service_analyze(
    days_since_last_login: int,
    total_spend: float,
    support_tickets_count: int,
    expected_is_high: bool,
    expected_score: float,
) -> None:
    model = MockChurnModel()
    service = ChurnAnalysisService(model=model)

    activity = CustomerActivity(
        days_since_last_login=days_since_last_login,
        total_spend=total_spend,
        support_tickets_count=support_tickets_count,
    )

    risk = service.analyze(activity)

    assert risk.is_high_risk is expected_is_high
    assert risk.risk_score == pytest.approx(expected_score)


def test_churn_analysis_service_support_adjust_clamps_to_zero() -> None:
    """
    Доп. кейс, чтобы покрыть ветку max(0, ...) для support_tickets_count.
    """

    service = ChurnAnalysisService(
        model=MockChurnModel(),
        config=ChurnServiceConfig(
            # Умышленно делаем decrement, чтобы max(0, ...) сработал.
            loyalty_threshold=999.0,
            days_increment_on_low_loyalty=25,
            support_increment_on_low_loyalty=-10,
        ),
    )

    activity = CustomerActivity(
        days_since_last_login=10,
        total_spend=10.0,
        support_tickets_count=3,
    )

    risk = service.analyze(activity)

    assert risk.is_high_risk is True  # по дням после adjust будет > 30
    assert risk.risk_score == pytest.approx(0.8)

