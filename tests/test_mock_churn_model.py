import pytest

from src.domain.entities import CustomerActivity
from src.infrastructure.churn_model import MockChurnModel


@pytest.mark.parametrize(
    "days_since_last_login,support_tickets_count,expected_is_high,expected_score",
    [
        (31, 0, True, 0.8),
        (30, 6, True, 0.8),
        (30, 5, False, 0.2),
        (10, 0, False, 0.2),
    ],
)
def test_mock_churn_model_predict_risk(
    days_since_last_login: int,
    support_tickets_count: int,
    expected_is_high: bool,
    expected_score: float,
) -> None:
    model = MockChurnModel()
    activity = CustomerActivity(
        days_since_last_login=days_since_last_login,
        total_spend=100.0,
        support_tickets_count=support_tickets_count,
    )

    risk = model.predict_risk(activity)

    assert risk.is_high_risk is expected_is_high
    assert risk.risk_score == pytest.approx(expected_score)

