from pydantic import BaseModel


class CustomerActivity(BaseModel):
    days_since_last_login: int
    total_spend: float
    support_tickets_count: int


class ChurnRisk(BaseModel):
    is_high_risk: bool
    risk_score: float

