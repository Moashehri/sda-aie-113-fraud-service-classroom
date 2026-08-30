"""Orchestration for scoring transactions."""

from typing import Protocol

from fraud_service.domain.entities import (
    FraudFeatures,
    ScoredTransaction,
    Transaction,
    extract_features,
)
from fraud_service.domain.policies import BLOCK_THRESHOLD, decide


class Model(Protocol):
    """Port implemented by a concrete probability model adapter."""

    @property
    def version(self) -> str:
        """Return the loaded model artefact's version."""
        ...

    def predict_probability(self, features: FraudFeatures) -> float:
        """Return the fraud probability for one feature vector."""
        ...


class FraudScorer:
    """Extract features, obtain a score, and apply the decision policy."""

    def __init__(self, model: Model, block_threshold: float = BLOCK_THRESHOLD) -> None:
        self._model = model
        self._block_threshold = block_threshold

    def score(self, transaction: Transaction) -> ScoredTransaction:
        features = extract_features(transaction)
        probability = self._model.predict_probability(features)
        return ScoredTransaction(
            transaction_id=transaction.transaction_id,
            score=probability,
            decision=decide(probability, self._block_threshold),
            model_version=self._model.version,
        )
