from __future__ import annotations

from src.application.services import ChurnAnalysisService, ChurnServiceConfig
from src.domain.interfaces import IChurnModel
from src.infrastructure.churn_model import MockChurnModel


def create_churn_analysis_service(
    *,
    model: IChurnModel | None = None,
    config: ChurnServiceConfig | None = None,
) -> ChurnAnalysisService:
    """
    Фабрика сборки сервиса (composition root в внешнем слое).

    Application/Domain остаются независимыми: здесь связываются интерфейсы и реализации.
    """

    resolved_model = model or MockChurnModel()
    resolved_config = config
    return ChurnAnalysisService(model=resolved_model, config=resolved_config)

