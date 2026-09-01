# Fraud Scoring Service (`fraud-service`)

Developed by: Moayad Alshehri

A high-performance, containerized, production-grade fraud detection microservice built with **Clean Architecture** in Python 3.12, **FastAPI**, and **scikit-learn** / **XGBoost**.

The service evaluates real-time financial transactions against pre-trained machine learning models and applies configurable business policy bands (`allow`, `review`, `block`) with strict request validation, correlated structured logging, and non-root container security.

---

## 1. Overview & Key Features

- **Clean Architecture Separation**: Pure, framework-agnostic domain and application layers isolated from HTTP delivery (FastAPI) and ML infrastructure (scikit-learn/joblib).
- **Strict API Schema Validation**: Zero-trust request validation with Pydantic v2 (`extra="forbid"`, bounded ranges, strict ISO 8601 timestamps, regex constraints).
- **Standardized Error Envelope**: Uniform response structures across validation, HTTP, and unexpected server exceptions, preventing internal stack trace leaks.
- **Operational Health & Readiness**: Distinct liveness (`/v1/health`) and readiness (`/v1/ready`) probes with lifespan model loading and synthetic transaction warm-up.
- **Privacy-Preserving Structured Logging**: Correlated JSON logs with `X-Trace-Id` request tracing and coarse probability bucketing (`"0.00-0.24"`, `"0.25-0.49"`, etc.) to prevent data leakage.
- **Multi-Tier Automated Testing**: 111 unit, integration, and behavioural acceptance tests with **99% statement coverage** and **95.8% branch coverage**.
- **Hardened Containerization**: Multi-stage Docker build producing a slim **160.6 MB** image executing under a non-root system user (`uid=999(fraud)`).
- **Automated CI/CD Pipeline**: GitHub Actions workflow running parallel linting, type checks, coverage gates (≥80%), container smoke tests, Trivy vulnerability scans, and immutable SHA-tagged image publishing to GHCR.

---

## 2. Technology Stack

- **Runtime & Language**: Python 3.12+
- **API Framework**: FastAPI, Uvicorn, Starlette
- **Data Validation & Settings**: Pydantic v2, Pydantic Settings
- **Machine Learning & Computation**: scikit-learn, XGBoost, Pandas, NumPy, Joblib
- **Testing & Quality Assurance**: Pytest, Pytest-Cov, Ruff, Mypy (strict), Import-Linter
- **Containerization & Orchestration**: Docker, Docker Compose, BuildKit
- **Performance Benchmarking**: Grafana k6
- **CI/CD & Security Scanning**: GitHub Actions, GHCR, Aqua Trivy, Gitleaks

---

## 3. Architecture & Layer Boundaries

The service follows **Clean Architecture** (Ports and Adapters). Core business logic imports zero third-party frameworks.

```
       ┌────────────────────────────────────────────────────────┐
       │                   Presentation Layer                   │
       │     FastAPI Routes (api/)     │   Batch CLI (batch.py) │
       └─────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
       ┌────────────────────────────────────────────────────────┐
       │                    Adapters Layer                      │
       │    SklearnModel (adapters/sklearn_model.py)            │
       └─────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
       ┌────────────────────────────────────────────────────────┐
       │                     Service Layer                      │
       │    FraudScorer, Model Protocol, FeatureRepo Protocol   │
       └─────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
       ┌────────────────────────────────────────────────────────┐
       │                     Domain Layer                       │
       │    Entities (Transaction, FraudFeatures, FraudScore)   │
       │    Policies (decide, allow/review/block bands)         │
       │    Feature Extraction (extract_features)               │
       └────────────────────────────────────────────────────────┘
```

### Layer Responsibilities & Dependency Direction

1. **`domain/`**:
   - `entities.py`: Pure dataclasses representing `Transaction`, derived `FraudFeatures`, and `FraudScore`. Contains deterministic mathematical feature derivations (e.g., `log1p(amount_sar)`, MCC normalization, nocturnal hour checks).
   - `policies.py`: Pure business decision logic evaluating calculated probabilities against threshold bands to produce `allow`, `review`, or `block` decisions.
   - *Dependencies*: Pure Python standard library only.
2. **`service/`**:
   - `interfaces.py`: Structural typing contracts (`typing.Protocol`) defining the `Model` port (`version`, `predict_probability`) and `FeatureRepo` port.
   - `scorer.py`: `FraudScorer` coordinates feature extraction, model inference through the `Model` protocol, and policy evaluation.
   - *Dependencies*: Imports only from `domain/`.
3. **`adapters/`**:
   - `sklearn_model.py`: Concrete adapter implementing the `Model` protocol using `joblib` and `scikit-learn`.
   - *Dependencies*: Imports from `domain/`, `service/`, and external ML libraries.
4. **`api/` & `batch.py`**:
   - `api/schemas.py`: Pydantic request/response/error schemas.
   - `api/routes.py`: FastAPI endpoints (`/v1/predict`, `/v1/health`, `/v1/ready`).
   - `api/app.py`: Application factory, lifespan management, warm-up, trace ID middleware, and global exception handlers.
   - `batch.py`: CLI composition root to score offline CSV datasets.
   - *Dependencies*: Composition root wiring adapters, service, and domain.

> Inward dependency direction is strictly verified in CI by `import-linter`. See [DECISIONS.md](DECISIONS.md) for full Architecture Decision Records.

---

## 4. Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── ci.yml                 # Multi-stage CI/CD pipeline
├── configs/
│   └── settings.example.env       # Safe configuration template
├── data/
│   ├── golden_scores_v3.csv       # Regression verification baseline
│   ├── holdout_eval.csv           # Model evaluation holdout set
│   └── transactions_sample.csv    # 5,000 synthetic transaction records
├── models/
│   └── fraud_xgb_v3.joblib        # Pre-trained ML pipeline bundle (Git LFS)
├── payloads/
│   ├── malformed/                 # 50+ malformed JSON payloads for contract testing
│   ├── valid/                     # 20 valid JSON payloads
│   └── sample.json                # Standard sample request payload
├── scripts/
│   ├── cache_rebuild.sh           # Docker cache discipline verification script
│   ├── loadtest.js                # k6 load testing script
│   ├── smoke.sh                   # API smoke testing script
│   └── startup_time.sh            # Cold-start / readiness timing script
├── src/
│   └── fraud_service/
│       ├── adapters/              # Infrastructure adapters (scikit-learn)
│       ├── api/                   # FastAPI application, routes, schemas
│       ├── domain/                # Pure business logic, entities, policies
│       ├── service/               # Application orchestration & protocols
│       ├── batch.py               # Batch CSV scoring entrypoint
│       ├── config.py              # Centralized typed Settings (Pydantic)
│       └── logging_setup.py       # JSON structured logging with trace ID
├── tests/
│   ├── behavioural/               # Tests against real ML model (invariance, golden)
│   ├── integration/               # API contract, middleware, and payload suite
│   ├── unit/                      # Fast unit tests using test doubles
│   └── conftest.py                # Shared fixtures and mock models
├── BENCHMARKS.md                  # Measured performance & benchmark records
├── DECISIONS.md                   # Engineering Architecture Decision Records (ADR)
├── docker-compose.yml             # Local dev stack (API + Redis cache + k6)
├── Dockerfile                     # Multi-stage production container definition
├── Dockerfile.naive               # Baseline single-stage container for comparison
├── Makefile                       # Developer and operations task runner
├── pyproject.toml                 # Project metadata, dependencies, tool configurations
├── README.md                      # Project documentation and guide
└── RUNBOOK.md                     # Operational troubleshooting and runbook
```

---

## 5. Prerequisites & Environment Setup

### Prerequisites
- **Python**: `3.12` or newer
- **Git** & **Git LFS**: Required for tracking pre-trained model artifacts
- **Docker** & **Docker Compose**: Required for containerized execution and load testing
- **Make**: Standard build automation tool

### 5.1 Clone & Git LFS Initialization
```bash
git clone https://github.com/Moashehri/sda-aie-113-fraud-service-classroom.git
cd sda-aie-113-fraud-service-classroom

# Pull tracked binary model artifacts
git lfs install
git lfs pull
```

### 5.2 Python Virtual Environment Setup
```bash
# Create a Python 3.12 virtual environment
python3.12 -m venv .venv

# Activate environment (Linux / macOS)
source .venv/bin/activate

# Activate environment (Windows PowerShell)
# .venv\Scripts\Activate.ps1
```

### 5.3 Dependency Installation
```bash
# Install package in editable mode with all development and test dependencies
pip install --upgrade pip
make install
# Or directly:
python -m pip install -e ".[dev]"
```

---

## 6. Configuration & Environment Variables

All settings are managed via `fraud_service.config.Settings` using the `FRAUD_` prefix.

Copy the example configuration file:
```bash
cp configs/settings.example.env .env
```

### Configuration Parameters

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `FRAUD_APP_NAME` | `string` | `fraud-service` | Service application name |
| `FRAUD_ENVIRONMENT` | `string` | `development` | Runtime environment (`development`, `test`, `production`) |
| `FRAUD_HOST` | `string` | `0.0.0.0` | Network interface to bind HTTP server |
| `FRAUD_PORT` | `integer` | `8000` | Network port (1–65535) |
| `FRAUD_MODEL_PATH` | `path` | `models/fraud_xgb_v3.joblib` | Path to pre-trained model artifact (validated at boot) |
| `FRAUD_BLOCK_THRESHOLD` | `float` | `0.85` | Score above which transaction is blocked (0.0–1.0) |
| `FRAUD_REVIEW_BAND_WIDTH` | `float` | `0.15` | Width below block threshold triggering review (0.0–1.0) |
| `FRAUD_LOG_LEVEL` | `string` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

> **Startup Validation**: If `FRAUD_MODEL_PATH` does not exist or `FRAUD_REVIEW_BAND_WIDTH > FRAUD_BLOCK_THRESHOLD`, the service fails fast and terminates immediately during boot.

---

## 7. Running the Service

### 7.1 Local Development Server
```bash
make run
# Or directly:
PYTHONPATH=src python -m fraud_service.api.app
```
The API is available at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

### 7.2 Batch Scoring Execution
To score the 5,000 transactions in `data/transactions_sample.csv` and output `scored.csv`:
```bash
make run-batch
# Or directly:
PYTHONPATH=src python -m fraud_service.batch
```

### 7.3 Containerized Stack (Docker & Compose)
```bash
# Build multi-stage production Docker image
make image

# Launch container stack with Redis cache in background
make up

# Run smoke test against running container
make smoke

# Execute k6 load test suite
make loadtest

# Stop and clean up containers
docker compose down
```

---

## 8. API Usage & Examples

### 8.1 Health & Readiness Probes

#### Liveness Probe (`GET /v1/health`)
```bash
curl -s http://localhost:8000/v1/health
```
```json
{
  "status": "ok"
}
```

#### Readiness Probe (`GET /v1/ready`)
```bash
curl -s http://localhost:8000/v1/ready
```
```json
{
  "status": "ready"
}
```

---

### 8.2 Prediction Endpoint (`POST /v1/predict`)

#### Example 1: Valid Prediction Request
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
  "fraud_probability": 0.04260341908722285,
  "decision": "allow",
  "model_version": "v3",
  "trace_id": "7f8b9e1a2c3d4e5f"
}
```

**Response Headers Include:**
- `X-Trace-Id`: Unique 16-character hexadecimal correlation identifier.
- `X-Process-Time`: Request processing duration in seconds (e.g. `0.003412`).

---

#### Example 2: Malformed Request (Validation Rejection)
```bash
curl -i -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-BAD",
    "amount_sar": -10.00,
    "channel": "crypto",
    "merchant_category": "SHOP",
    "customer_id": "CUST-1",
    "timestamp": "not-a-timestamp",
    "extra_field": "disallowed"
  }'
```

**Expected Response (HTTP 422 Unprocessable Entity):**
```json
{
  "error": "Validation Error",
  "trace_id": "9b2c3d4e5f67890a",
  "details": {
    "errors": [
      {
        "location": ["body", "transaction_id"],
        "message": "String should have at least 10 characters",
        "type": "string_too_short"
      },
      {
        "location": ["body", "amount_sar"],
        "message": "Input should be greater than 0",
        "type": "greater_than"
      },
      {
        "location": ["body", "channel"],
        "message": "Input should be 'pos', 'ecom', 'atm' or 'transfer'",
        "type": "literal_error"
      },
      {
        "location": ["body", "timestamp"],
        "message": "Value error, timestamp must be an ISO 8601 string",
        "type": "value_error"
      },
      {
        "location": ["body", "extra_field"],
        "message": "Extra inputs are not permitted",
        "type": "extra_forbidden"
      }
    ]
  }
}
```

---

## 9. Verification & Testing

Execute the complete quality and testing suite locally:

```bash
# 1. Run full test suite with coverage report
pytest --cov=fraud_service --cov-branch --cov-report=term-missing

# 2. Run fast unit tests only
pytest -m unit

# 3. Run integration tests (API schemas, error handling, 70+ payloads)
pytest -m integration

# 4. Run behavioural acceptance tests (invariance, monotonicity, golden scores)
pytest -m behavioural

# 5. Run Ruff linter and code format checks
ruff check src tests
ruff format --check src tests

# 6. Run strict static type checking
mypy src/fraud_service --strict

# 7. Run architectural layer boundary verification
PYTHONPATH=src lint-imports
```

---

## 10. CI/CD & Build Pipeline

The automated GitHub Actions workflow (`.github/workflows/ci.yml`) executes on every pull request and push to `main`:

1. **`lint` job**: Runs Ruff format check, Ruff linter, strict Mypy type checks, and Import-Linter layer contract enforcement.
2. **`test` job**: Executes the full test suite with pytest, enforcing a strict **`--cov-fail-under=80`** branch coverage gate, and uploads coverage artifacts.
3. **`image-smoke` job**: Builds the multi-stage Docker image with BuildKit caching, starts the container, runs the end-to-end smoke test (`scripts/smoke.sh`), and scans the image for vulnerabilities using **Aqua Trivy** (`exit-code: 1` on critical/high CVEs).
4. **`publish` job** (runs only on `main` push): Publishes the tested image to GitHub Container Registry (GHCR) tagged with the immutable commit SHA (`ghcr.io/<repo>:<sha>`) and the floating `main` tag.

---

## 11. Troubleshooting & Support

| Issue | Cause | Solution |
| --- | --- | --- |
| `ValueError: model artefact does not exist` | Git LFS pointer instead of binary, or bad path | Run `git lfs pull` and verify `models/fraud_xgb_v3.joblib` size (~42 KB). |
| `ValueError: review_band_width cannot exceed...` | Misconfigured threshold bands | Adjust `FRAUD_REVIEW_BAND_WIDTH` in `.env` so it is $\le \text{FRAUD\_BLOCK\_THRESHOLD}$. |
| `HTTP 503 Service Unavailable` on `/v1/ready` | Model is still loading or initialization failed | Check startup logs: `docker compose logs fraud-api`. |
| Port conflict on 8000 | Another process is using port 8000 | Set `FRAUD_PORT=8080` in `.env` or run `FRAUD_PORT=8080 make run`. |

For in-depth recovery steps, container debugging, and incident response guides, see the [Operations Runbook](RUNBOOK.md).

---

## 12. Engineering Decisions & Benchmarks

- **[DECISIONS.md](DECISIONS.md)**: Architectural Decision Records (ADRs) detailing trade-offs in Clean Architecture, Pydantic validation, model protocols, test doubles, non-root execution, and logging privacy.
- **[BENCHMARKS.md](BENCHMARKS.md)**: Verified benchmark records covering test execution speed, coverage percentages, cold/warm Docker build times, and k6 load test latency distributions.
- **[RUNBOOK.md](RUNBOOK.md)**: Operational guide for deploying, monitoring, tracing, and debugging the service in production.

---

## 13. Training Attribution

This project was developed and completed under **SDAIA Academy**.
Developed by: Moayad Alshehri

- **Course**: `SDA-AIE-113 — Software Engineering Practices for AI Systems`
- **Official Organization**: [SDAIA Academy on GitHub](https://github.com/SDAIA-Academy)

*(Note: In accordance with verification protocols, course identification is reported directly from verified course curriculum sources without unverified overarching cohort designations.)*
