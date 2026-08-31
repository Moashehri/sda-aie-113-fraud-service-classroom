"""Tests for scoring orchestration and protocol seams."""

from datetime import UTC, datetime

import pytest

from fraud_service.domain.entities import FraudFeatures, Transaction
from fraud_service.domain.policies import Decision
from fraud_service.service.scorer import FraudScorer

pytestmark = pytest.mark.unit


class RecordingModel:
    version = "fake-v2"

    def __init__(self) -> None:
        self.features: FraudFeatures | None = None

    def predict_probability(self, features: FraudFeatures) -> float:
        self.features = features
        return 0.9


class FixedFeatureRepo:
    def get_features(self, transaction: Transaction) -> FraudFeatures:
        return FraudFeatures(1.0, "atm", "TEST", 3, 1)


def test_scorer_uses_protocols_and_applies_policy() -> None:
    model = RecordingModel()
    scorer = FraudScorer(model=model, feature_repo=FixedFeatureRepo())
    transaction = Transaction(
        "TXN-TEST-0003",
        10.0,
        "pos",
        "GROCERY",
        "CUST-3",
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = scorer.score(transaction)

    assert model.features == FraudFeatures(1.0, "atm", "TEST", 3, 1)
    assert result.transaction_id == transaction.transaction_id
    assert result.score == 0.9
    assert result.decision is Decision.BLOCK
    assert result.model_version == "fake-v2"
