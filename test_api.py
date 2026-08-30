from fastapi.testclient import TestClient
from fraud_service.api.app import app

with TestClient(app) as client:
    response = client.get("/v1/health")
    print("Health:", response.json())

    response = client.get("/v1/ready")
    print("Ready:", response.json())

    payload = {
        "transaction_id": "TXN-2026-00042",
        "amount_sar": 150.0,
        "channel": "ecom",
        "merchant_category": "electronics",
        "customer_id": "CUST-123",
        "timestamp": "2026-08-30T10:00:00Z"
    }
    response = client.post("/v1/predict", json=payload)
    print("Predict:", response.json())
