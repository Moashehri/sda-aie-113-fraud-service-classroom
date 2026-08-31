"""Behavioural checks against the real model artefact."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.domain.entities import Transaction
from fraud_service.service.scorer import FraudScorer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_xgb_v3.joblib"

pytestmark = pytest.mark.behavioural


@pytest.fixture(scope="module")
def scorer() -> FraudScorer:
    return FraudScorer(SklearnModel.load(MODEL_PATH))


def _transaction(amount: float, merchant: str = "ELECTRONICS") -> Transaction:
    return Transaction(
        transaction_id="TXN-BEHAVIOUR-1",
        amount_sar=amount,
        channel="ecom",
        merchant_category=merchant,
        customer_id="CUST-1",
        timestamp=datetime(2026, 7, 5, 22, 14, tzinfo=UTC),
    )


def test_merchant_category_normalization_is_invariant(scorer: FraudScorer) -> None:
    canonical = scorer.score(_transaction(412.5, "ELECTRONICS"))
    normalized = scorer.score(_transaction(412.5, "  electronics  "))
    assert normalized.score == pytest.approx(canonical.score)


def test_larger_amount_has_higher_model_score(scorer: FraudScorer) -> None:
    assert (
        scorer.score(_transaction(10_000)).score > scorer.score(_transaction(10)).score
    )


def test_model_matches_golden_scores(scorer: FraudScorer) -> None:
    transactions = pd.read_csv(PROJECT_ROOT / "data" / "transactions_sample.csv")
    golden = pd.read_csv(PROJECT_ROOT / "data" / "golden_scores_v3.csv")

    expected = dict(zip(golden["transaction_id"], golden["score"], strict=True))
    for row in transactions.head(25).to_dict(orient="records"):
        result = scorer.score(Transaction.from_mapping(row))
        assert result.score == pytest.approx(expected[result.transaction_id], abs=1e-12)
