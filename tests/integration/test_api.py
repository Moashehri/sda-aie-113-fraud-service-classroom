"""API contract and component integration tests."""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PAYLOADS = Path(__file__).resolve().parents[2] / "payloads"
MALFORMED_PAYLOADS = sorted((PAYLOADS / "malformed").glob("*.json"))
VALID_PAYLOADS = sorted((PAYLOADS / "valid").glob("*.json"))

pytestmark = pytest.mark.integration


def test_health_readiness_and_prediction_contract(client: TestClient) -> None:
    assert client.get("/v1/health").json() == {"status": "ok"}
    assert client.get("/v1/ready").json() == {"status": "ready"}

    payload = json.loads((PAYLOADS / "sample.json").read_text())
    response = client.post("/v1/predict", json=payload)

    assert response.status_code == 200
    assert response.headers["x-trace-id"]
    assert float(response.headers["x-process-time"]) >= 0.0
    assert response.json() == {
        "transaction_id": payload["transaction_id"],
        "fraud_probability": 0.72,
        "decision": "review",
        "model_version": "test-v1",
        "trace_id": response.headers["x-trace-id"],
    }


def test_readiness_and_prediction_are_unavailable_before_lifespan(
    application: FastAPI,
) -> None:
    unmanaged_client = TestClient(application, raise_server_exceptions=False)
    try:
        ready_response = unmanaged_client.get("/v1/ready")
        assert ready_response.status_code == 503
        assert ready_response.headers["content-type"].startswith("application/json")
        assert ready_response.json() == {
            "error": "Model is not ready",
            "trace_id": ready_response.headers["x-trace-id"],
            "details": None,
        }

        payload = json.loads((PAYLOADS / "sample.json").read_text())
        prediction_response = unmanaged_client.post("/v1/predict", json=payload)
        assert prediction_response.status_code == 503
        assert prediction_response.json()["error"] == "Model is not ready"
        assert (
            prediction_response.json()["trace_id"]
            == prediction_response.headers["x-trace-id"]
        )
    finally:
        unmanaged_client.close()


@pytest.mark.parametrize("payload_path", VALID_PAYLOADS, ids=lambda path: path.stem)
def test_valid_payload_corpus_is_accepted(
    client: TestClient, payload_path: Path
) -> None:
    response = client.post(
        "/v1/predict",
        content=payload_path.read_bytes(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("payload_path", MALFORMED_PAYLOADS, ids=lambda path: path.stem)
def test_malformed_payload_corpus_is_rejected(
    client: TestClient, payload_path: Path
) -> None:
    response = client.post(
        "/v1/predict",
        content=payload_path.read_bytes(),
        headers={"content-type": "application/json"},
    )
    assert 400 <= response.status_code < 500
    assert response.json()["trace_id"] == response.headers["x-trace-id"]


def test_unhandled_error_uses_safe_envelope(
    application: FastAPI, client: TestClient
) -> None:
    @application.get("/boom")
    def boom() -> None:
        raise RuntimeError("private implementation detail")

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"] == "Internal Server Error"
    assert response.json()["trace_id"] == response.headers["x-trace-id"]
    assert "private implementation detail" not in response.text
