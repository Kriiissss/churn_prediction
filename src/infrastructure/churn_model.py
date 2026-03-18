from src.domain.entities import ChurnRisk, CustomerActivity
from src.domain.interfaces import IChurnModel


class MockChurnModel(IChurnModel):
    """
    Mock-модель, имитирующая предсказание вероятности оттока.
    """

    def predict_risk(self, activity: CustomerActivity) -> ChurnRisk:
        is_high_risk = (activity.days_since_last_login > 30) or (
            activity.support_tickets_count > 5
        )
        risk_score = 0.8 if is_high_risk else 0.2
        return ChurnRisk(is_high_risk=is_high_risk, risk_score=risk_score)

