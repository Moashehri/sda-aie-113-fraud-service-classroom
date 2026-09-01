"""Tests for privacy-conscious structured logging."""

import io
import json
import logging

import pytest

from fraud_service.logging_setup import (
    JsonFormatter,
    probability_bucket,
    trace_id_context,
)

pytestmark = pytest.mark.unit


def test_json_logs_are_correlated_and_omit_unsafe_fields() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("audit.logging-test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    token = trace_id_context.set("trace-test-123")
    try:
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "method": "POST",
                "path": "/v1/predict",
                "status_code": 200,
                "customer_id": "CUST-PRIVATE",
                "request_body": {"amount_sar": 999.0},
                "authorization": "Bearer private-token",
                "password": "private-password",
            },
        )
        logger.info(
            "prediction_served",
            extra={
                "event": "prediction_served",
                "decision": "allow",
                "probability_bucket": probability_bucket(0.1),
                "model_version": "test-v1",
                "amount_sar": 999.0,
                "transaction_id": "TXN-PRIVATE",
            },
        )
    finally:
        trace_id_context.reset(token)
        logger.removeHandler(handler)

    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(records) == 2
    assert {record["trace_id"] for record in records} == {"trace-test-123"}
    assert records[0]["event"] == "request_completed"
    assert records[1]["event"] == "prediction_served"
    assert records[1]["probability_bucket"] == "0.00-0.24"
    unsafe_fields = {
        "customer_id",
        "request_body",
        "authorization",
        "password",
        "amount_sar",
        "transaction_id",
    }
    assert unsafe_fields.isdisjoint(records[0])
    assert unsafe_fields.isdisjoint(records[1])


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.24, "0.00-0.24"),
        (0.25, "0.25-0.49"),
        (0.49, "0.25-0.49"),
        (0.50, "0.50-0.74"),
        (0.74, "0.50-0.74"),
        (0.75, "0.75-1.00"),
    ],
)
def test_probability_bucket_has_explicit_boundaries(
    probability: float, expected: str
) -> None:
    assert probability_bucket(probability) == expected
