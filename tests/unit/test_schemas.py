"""Tests for request validation boundaries."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fraud_service.api.schemas import PredictRequest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 1, 1, 10, tzinfo=UTC),
        "2026-01-01 10:30:00+00:00",
        "2026-01-01Tnot-a-datetime+00:00",
        "2026-01-01T10:30:00",
    ],
)
def test_timestamp_validation_rejects_non_iso_or_naive_values(
    timestamp: object,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        PredictRequest(
            transaction_id="TXN-SCHEMA-0001",
            amount_sar=10.0,
            channel="pos",
            merchant_category="GROCERY",
            customer_id="CUST-SCHEMA-1",
            timestamp=timestamp,
        )

    error = exc_info.value.errors()[0]
    assert error["loc"] == ("timestamp",)
    assert "timestamp" in error["msg"]
