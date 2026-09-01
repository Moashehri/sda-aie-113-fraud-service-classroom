from datetime import UTC, datetime

import pytest

from fraud_service.domain.entities import Transaction, extract_features


@pytest.mark.unit
def test_merchant_category_is_normalized() -> None:
    """Ensure merchant category is properly formatted during feature extraction."""
    txn = Transaction(
        transaction_id="test-1",
        amount_sar=100.0,
        channel="web",
        merchant_category="  reTaIL  Shop ",
        customer_id="cust-1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    features = extract_features(txn)
    # The domain model does: merchant_category.strip().upper().replace(" ", "_")
    assert features.mcc == "RETAIL__SHOP"


@pytest.mark.unit
def test_night_flag() -> None:
    """Check if the night flag is correctly set at the boundary hour."""
    # Night is defined as hour < 6 (00:00 to 05:59)
    txn_night = Transaction(
        transaction_id="test-2",
        amount_sar=100.0,
        channel="web",
        merchant_category="retail",
        customer_id="cust-1",
        timestamp=datetime(2026, 1, 1, 5, 59, tzinfo=UTC),  # 05:59 AM is night
    )
    features_night = extract_features(txn_night)
    assert features_night.is_night == 1

    txn_day = Transaction(
        transaction_id="test-3",
        amount_sar=100.0,
        channel="web",
        merchant_category="retail",
        customer_id="cust-1",
        timestamp=datetime(2026, 1, 1, 6, 0, tzinfo=UTC),  # 06:00 AM is day
    )
    features_day = extract_features(txn_day)
    assert features_day.is_night == 0
