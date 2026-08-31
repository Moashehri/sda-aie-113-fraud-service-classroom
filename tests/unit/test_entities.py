"""Tests for framework-free feature extraction."""

from datetime import UTC, datetime
from math import log1p

import pytest

from fraud_service.domain.entities import Transaction, extract_features

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("hour", "is_night"),
    [(0, 1), (5, 1), (6, 0), (23, 0)],
)
def test_extract_features_normalizes_values(hour: int, is_night: int) -> None:
    transaction = Transaction(
        transaction_id="TXN-TEST-0001",
        amount_sar=99.0,
        channel="ecom",
        merchant_category="  home goods  ",
        customer_id="CUST-1",
        timestamp=datetime(2026, 1, 1, hour, tzinfo=UTC),
    )

    features = extract_features(transaction)

    assert features.amount_log == pytest.approx(log1p(99.0))
    assert features.mcc == "HOME_GOODS"
    assert features.hour_of_day == hour
    assert features.is_night == is_night


def test_transaction_can_be_created_from_a_csv_mapping() -> None:
    transaction = Transaction.from_mapping(
        {
            "transaction_id": "TXN-TEST-0002",
            "amount_sar": "12.50",
            "channel": "pos",
            "merchant_category": "GROCERY",
            "customer_id": "CUST-2",
            "timestamp": "2026-01-01T10:30:00Z",
        }
    )

    assert transaction.amount_sar == 12.5
    assert transaction.timestamp.tzinfo is not None
