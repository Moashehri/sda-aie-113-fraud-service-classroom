"""Orchestration for scoring transactions."""

from fraud_service.domain.entities import (
    FraudScore,
    Transaction,
    extract_features,
)
from fraud_service.domain.policies import (
    BLOCK_THRESHOLD,
    REVIEW_BAND_WIDTH,
    decide,
)
from fraud_service.service.interfaces import FeatureRepo, Model


class FraudScorer:
    """Extract features, obtain a score, and apply the decision policy."""

    def __init__(
        self,
        model: Model,
        block_threshold: float = BLOCK_THRESHOLD,
        review_band_width: float = REVIEW_BAND_WIDTH,
        feature_repo: FeatureRepo | None = None,
    ) -> None:
        self._model = model
        self._block_threshold = block_threshold
        self._review_band_width = review_band_width
        self._feature_repo = feature_repo

    def score(self, transaction: Transaction) -> FraudScore:
        features = (
            self._feature_repo.get_features(transaction)
            if self._feature_repo is not None
            else extract_features(transaction)
        )
        probability = self._model.predict_probability(features)
        return FraudScore(
            transaction_id=transaction.transaction_id,
            score=probability,
            decision=decide(
                probability,
                block_threshold=self._block_threshold,
                review_band_width=self._review_band_width,
            ),
            model_version=self._model.version,
        )
