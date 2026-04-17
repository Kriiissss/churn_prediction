from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import ChurnRisk, CustomerActivity
from src.domain.interfaces import IChurnModel, IModel


@dataclass(frozen=True, slots=True)
class ChurnServiceConfig:
    # Порог лояльности, ниже которого риск будет немного увеличен.
    loyalty_threshold: float = 20.0

    # Насколько "усиливаем" признак при низкой лояльности.
    days_increment_on_low_loyalty: int = 25
    support_increment_on_low_loyalty: int = 1


class ChurnAnalysisService:
    """
    Use-case для расчета риска оттока.

    Важно: ML-логика скрыта за интерфейсом IChurnModel, на этом этапе используются mock-реализации.
    """

    def __init__(self, model: IChurnModel, config: ChurnServiceConfig | None = None) -> None:
        self._model = model
        self._config = config or ChurnServiceConfig()

    def analyze(self, activity: CustomerActivity) -> ChurnRisk:
        loyalty = self._calculate_loyalty(activity)
        adjusted_activity = self._adjust_activity_if_needed(activity, loyalty)
        return self._model.predict_risk(adjusted_activity)

    def _calculate_loyalty(self, activity: CustomerActivity) -> float:
        return activity.total_spend / (activity.support_tickets_count + 1)

    def _adjust_activity_if_needed(self, activity: CustomerActivity, loyalty: float) -> CustomerActivity:
        if loyalty >= self._config.loyalty_threshold:
            return activity

        return CustomerActivity(
            days_since_last_login=max(0, activity.days_since_last_login + self._config.days_increment_on_low_loyalty),
            total_spend=activity.total_spend,
            support_tickets_count=max(0, activity.support_tickets_count + self._config.support_increment_on_low_loyalty),
        )


class InferenceService:
    """
    Use-case: inference определения языка текста.

    Логика:
      - передаем текст(ы) в IModel
      - берём max(probabilities)
      - возвращаем (language_code, confidence)
    """

    def __init__(self, model: IModel) -> None:
        self._model = model

    def predict(self, text: str) -> tuple[str, float]:
        # Нормализуем регистр здесь, т.к. pipeline обучается с lowercase=False.
        probabilities, labels = self._model.predict([text.lower()])

        # probabilities: [1, num_classes]
        row = probabilities[0]
        best_idx = max(range(len(row)), key=lambda i: row[i])
        return labels[best_idx], float(row[best_idx])

