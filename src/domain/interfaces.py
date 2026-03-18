from abc import ABC, abstractmethod

from .entities import ChurnRisk, CustomerActivity


class IChurnModel(ABC):
    @abstractmethod
    def predict_risk(self, activity: CustomerActivity) -> ChurnRisk:
        raise NotImplementedError

