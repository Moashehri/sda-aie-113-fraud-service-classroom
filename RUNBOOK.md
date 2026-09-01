# Operations Runbook — Fraud Service

This runbook outlines operational procedures, troubleshooting steps, diagnostic commands, and failure recovery protocols for the **fraud-service**.

---

## 1. Quick Start & Execution

### 1.1 Local Development Environment

```bash
# 1. Activate the Python 3.12 virtual environment
source .venv/bin/activate

# 2. Copy and customize configuration
cp configs/settings.example.env .env

# 3. Start the FastAPI service
make run
# Or directly:
PYTHONPATH=src python -m fraud_service.api.app
```

The service will bind to `http://0.0.0.0:8000` by default.

### 1.2 Batch Scoring Mode

To score offline datasets from `data/transactions_sample.csv` and generate `scored.csv`:

```bash
make run-batch
# Or directly:
PYTHONPATH=src python -m fraud_service.batch
```

### 1.3 Containerized Stack (Docker Compose)

Start the full stack (API service + Redis feature cache):

```bash
# Build and launch containers in the background
make up

# View running container status
docker compose ps
```

---

## 2. Health & Readiness Verification

The service provides dedicated liveness and readiness endpoints:

### Liveness Probe (`GET /v1/health`)
Confirms the Python process and HTTP server are running.

```bash
curl -i http://localhost:8000/v1/health
```

**Expected Response (HTTP 200 OK):**
```json
{
  "status": "ok"
}
```

### Readiness Probe (`GET /v1/ready`)
Confirms the ML model artifact is loaded into memory, validated, and warmed up.

```bash
curl -i http://localhost:8000/v1/ready
```

**Expected Response (HTTP 200 OK):**
```json
{
  "status": "ready"
}
```

> **Note:** If the model has not loaded or failed initialization, `/v1/ready` returns `HTTP 503 Service Unavailable` with `{"error": "Model is not ready"}`.

---

## 3. Serving Predictions

### 3.1 Sending a Valid Prediction Request

```bash
curl -i -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-2026-00042",
    "amount_sar": 150.00,
    "channel": "ecom",
    "merchant_category": "ELECTRONICS",
    "customer_id": "CUST-0042",
    "timestamp": "2026-07-05T22:14:00Z"
  }'
```

**Expected Response (HTTP 200 OK):**
```json
{
  "transaction_id": "TXN-2026-00042",
  "fraud_probability": 0.042603,
  "decision": "allow",
  "model_version": "v3",
  "trace_id": "7f8b9e1a2c3d4e5f"
}
```

### 3.2 Sending a Malformed Request (Validation Failure)

```bash
curl -i -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-INVALID",
    "amount_sar": -50.00,
    "channel": "crypto",
    "merchant_category": "",
    "customer_id": "CUST-01",
    "timestamp": "invalid-date"
  }'
```

**Expected Response (HTTP 422 Unprocessable Entity):**
```json
{
  "error": "Validation Error",
  "trace_id": "8a1b2c3d4e5f6789",
  "details": {
    "errors": [
      {
        "location": ["body", "amount_sar"],
        "message": "Input should be greater than 0",
        "type": "greater_than"
      },
      {
        "location": ["body", "channel"],
        "message": "Input should be 'pos', 'ecom', 'atm' or 'transfer'",
        "type": "literal_error"
      }
    ]
  }
}
```

---

## 4. Observability & Log Analysis

### 4.1 Structured JSON Logs
The service outputs structured, line-delimited JSON logs to `stdout`. Every log line includes a timestamp, log level, logger name, and correlated `trace_id`.

```json
{"timestamp":"2026-09-01T12:00:00.123456+00:00","level":"INFO","logger":"fraud_service.api.routes","message":"prediction_served","trace_id":"7f8b9e1a2c3d4e5f","decision":"allow","probability_bucket":"0.00-0.24","model_version":"v3"}
{"timestamp":"2026-09-01T12:00:00.125678+00:00","level":"INFO","logger":"fraud_service.api.app","message":"request_completed","trace_id":"7f8b9e1a2c3d4e5f","duration_ms":3.45,"method":"POST","path":"/v1/predict","status_code":200}
```

### 4.2 Privacy Protection
To prevent leakage of sensitive financial data and reverse engineering of scoring thresholds:
- Exact raw floating-point probabilities are **never** logged to stdout.
- Probabilities are categorized into coarse `probability_bucket` values (`"0.00-0.24"`, `"0.25-0.49"`, `"0.50-0.74"`, `"0.75-1.00"`).
- Card details and customer PII are not persisted or logged.

### 4.3 Tracing Requests via Trace ID
Every HTTP response includes an `X-Trace-Id` header matching the JSON log entries:

```bash
# Filter container logs by specific trace ID
docker compose logs fraud-api | grep "7f8b9e1a2c3d4e5f"
```

---

## 5. Troubleshooting & Incident Recovery

### 5.1 Missing or Invalid Model Artefact
**Symptoms:** Service fails to start with `ValueError: model artefact does not exist`.

**Root Cause:**
- `FRAUD_MODEL_PATH` points to a non-existent path.
- Git LFS was not initialized, leaving a pointer file instead of the binary model bundle.

**Remediation:**
```bash
# Check if Git LFS pulled the actual file
git lfs pull

# Verify file size (should be ~42 KB, not a 130-byte text pointer)
ls -lh models/fraud_xgb_v3.joblib

# Confirm model path in environment
export FRAUD_MODEL_PATH="models/fraud_xgb_v3.joblib"
```

### 5.2 Misconfigured Decision Thresholds
**Symptoms:** Service fails during startup validation with `ValueError: review_band_width cannot exceed block_threshold`.

**Remediation:**
Check `.env` or container environment variables. Ensure:
$$ \text{FRAUD\_REVIEW\_BAND\_WIDTH} \le \text{FRAUD\_BLOCK\_THRESHOLD} $$
Recommended defaults:
```env
FRAUD_BLOCK_THRESHOLD=0.85
FRAUD_REVIEW_BAND_WIDTH=0.15
```

### 5.3 Container Fails Readiness Check
**Symptoms:** `docker compose ps` shows `fraud-api` status as `unhealthy` or `starting`.

**Diagnosis:**
```bash
# Inspect container healthcheck output and logs
docker inspect --format='{{json .State.Health}}' fraud-service-fraud-api-1 | jq
docker compose logs fraud-api --tail 50
```

**Remediation:**
- Ensure Redis (`feature-cache`) is healthy (`depends_on: condition: service_healthy`).
- Verify model bundle was copied into the container image at `/app/models/fraud_xgb_v3.joblib`.
- Test readiness manually inside container:
  ```bash
  docker compose exec fraud-api curl -s http://127.0.0.1:8000/v1/ready
  ```

### 5.4 Port Collision on Port 8000
**Symptoms:** `OSError: [Errno 48] Address already in use`.

**Remediation:**
```bash
# Identify process occupying port 8000
lsof -i :8000

# Override port via environment variable
FRAUD_PORT=8080 make run
```

---

## 6. Testing & CI Pipeline Troubleshooting

### 6.1 Running Local Test Suites
```bash
# Fast test suite
pytest -m "not slow"

# Behavioural tests against real model
pytest -m behavioural

# Full test suite with branch coverage gate
pytest --cov=fraud_service --cov-branch --cov-report=term-missing --cov-fail-under=80

# Linting & code style
ruff check src tests
ruff format --check src tests
mypy src/fraud_service --strict
PYTHONPATH=src lint-imports
```

### 6.2 CI Workflow Failures (`ci.yml`)
- **Lint job failure:** Run `ruff check --fix src tests` and `ruff format src tests`. Ensure `mypy` strict typing passes.
- **Coverage failure:** Ensure branch coverage is at least 80%. Check `coverage.xml` report.
- **Smoke test failure:** Check `scripts/smoke.sh` output. Ensure `payloads/sample.json` is intact and model is loaded.
- **Trivy scan failure:** Ensure base image `python:3.12-slim` is up to date and dependencies have no known critical vulnerabilities.

---

## 7. Shutdown & Resource Cleanup

### 7.1 Local Processes
Press `Ctrl+C` in the running terminal. The application lifespan handler gracefully cleans up state.

### 7.2 Docker & Compose Cleanup
```bash
# Stop and remove containers and network
docker compose down

# Stop containers and remove volumes/orphans
docker compose down -v --remove-orphans

# Clean up dangling images
docker image prune -f
```
