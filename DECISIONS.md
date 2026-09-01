# Engineering Architecture & Design Decisions (ADR)

This document records the architectural and engineering trade-offs made during the development of the **fraud-service**. Each decision outlines the context, the decision adopted, alternatives evaluated, and the resulting engineering consequences.

---

## ADR-001: Clean Architecture and Inward Dependency Enforcement

### Context
Machine learning scoring systems often suffer from tight coupling between business rules, feature transformations, framework dependencies (e.g., FastAPI, scikit-learn, Pandas), and execution environments. In the initial prototype (`notebook_v1.ipynb`), model execution, threshold logic, and feature transformations were intermingled, making testing and maintenance difficult.

### Decision
We structured the codebase following Clean Architecture principles into four distinct layers under `src/fraud_service/`:
1. **`domain/`**: Pure business logic (entities, feature extraction logic, allow/review/block decision policies). Zero external framework dependencies.
2. **`service/`**: Application use case orchestration and protocol definitions (`Model`, `FeatureRepo`, `FraudScorer`).
3. **`adapters/`**: Infrastructure and third-party integrations (such as `SklearnModel` wrapping scikit-learn/joblib).
4. **`api/` & `batch.py`**: Presentation and transport entrypoints (FastAPI HTTP routing, CLI batch scoring).

The dependency direction flows strictly inward: `api` / `batch` → `adapters` → `service` → `domain`. This invariant is formally enforced in CI via `import-linter` contracts configured in `pyproject.toml`.

### Alternatives Considered
- *Monolithic single-module structure*: Fast to implement but difficult to test and maintain over time.
- *Framework-centric structure (FastAPI-first)*: Embedding scoring logic directly into HTTP route handlers, which would prevent reuse by the batch CLI and make testing reliant on HTTP test clients.

### Consequences
- **Positive**: Core domain logic can be tested in sub-millisecond unit tests without loading ML models or spinning up HTTP servers.
- **Positive**: Changing the web framework or replacing scikit-learn with ONNX Runtime requires changes only in adapter and API layers without affecting business policies.
- **Trade-off**: Requires explicit data transfer mapping between API schemas, domain entities, and model feature vectors.

---

## ADR-002: Model Protocol Abstraction and Adapter Seam

### Context
Scikit-learn and XGBoost pipelines have large dependency trees, require disk I/O to unpickle, and incur non-trivial execution overhead during automated unit and API testing.

### Decision
We introduced a structural typing contract `Model(Protocol)` in `fraud_service.service.interfaces` requiring only:
- `version -> str`
- `predict_probability(features: FraudFeatures) -> float`

The concrete `SklearnModel` adapter in `fraud_service.adapters.sklearn_model` implements this protocol by loading the joblib bundle and executing `predict_proba`. The application composition roots (`create_app` and `run_batch`) accept a `model_factory` callable, defaulting to `SklearnModel.load`.

### Alternatives Considered
- *Direct import and instantiation of joblib in the service layer*: Creates a hard coupling to scikit-learn and prevents testing without real model files.
- *Abstract Base Classes (ABCs)*: Requires explicit inheritance, increasing coupling between adapters and the service layer compared to structural typing (`typing.Protocol`).

### Consequences
- **Positive**: Test suites can inject deterministic in-memory `FixedModel` test doubles, enabling fast unit and integration testing without disk I/O or sklearn dependencies.
- **Positive**: Enables easy future support for ONNX, Triton, or TensorRT model runtimes without modifying `FraudScorer`.
- **Trade-off**: Requires maintaining mapping methods (`as_mapping()`) to translate domain features into the tabular formats expected by scikit-learn.

---

## ADR-003: Strict API Validation and Standardized Error Envelope

### Context
Public ML inference APIs are vulnerable to malformed payloads, injection vectors, type coercion bugs, and internal information leakage via unhandled tracebacks.

### Decision
We defined rigid Pydantic v2 schemas in `fraud_service.api.schemas`:
- `extra="forbid"` on all request schemas to reject unexpected or malicious input keys.
- Strict bounded numeric validation (e.g., `amount_sar > 0` and `amount_sar <= 1,000,000`, `allow_inf_nan=False`).
- Strict regex and length constraints on transaction and customer identifiers (`^[A-Za-z0-9][A-Za-z0-9_-]*$`).
- Strict ISO 8601 parsing requiring explicit timezone offsets.
- A standardized `ErrorEnvelope(error: str, trace_id: str, details: ...)` returned across 400, 422, and 500 status codes.
- Global exception handlers that capture unhandled exceptions, log internal error details alongside the request `trace_id`, and return a sanitized `500 Internal Server Error` response to prevent stack trace leaks.

### Alternatives Considered
- *Default FastAPI/Pydantic validation schemas*: By default allows extra fields and returns raw Pydantic validation error trees without consistent correlation identifiers.
- *Returning detailed Python exception tracebacks*: Exposes internal implementation details and filesystem paths, introducing security risks.

### Consequences
- **Positive**: 100% of malformed payloads in the 50+ test corpus are safely rejected with clean 422 responses.
- **Positive**: Clients receive consistent error payloads containing correlation `trace_id` values matching HTTP `X-Trace-Id` headers for operational debugging.
- **Trade-off**: Requires strict client adherence to datetime formatting and input constraints.

---

## ADR-004: Health (`/v1/health`) vs Readiness (`/v1/ready`) Probes

### Context
In container orchestration environments (Kubernetes, Docker Compose, AWS ECS), routing traffic to a service before its ML model is initialized causes immediate 500 errors or high cold-start latencies.

### Decision
We split operational diagnostics into two endpoints:
- `GET /v1/health`: Liveness probe. Returns HTTP 200 `{"status": "ok"}` as soon as the HTTP server process is running.
- `GET /v1/ready`: Readiness probe. Returns HTTP 200 `{"status": "ready"}` only when the model artefact has been loaded, validated, and warmed up in application memory. Returns HTTP 503 if the model is not ready.

### Alternatives Considered
- *Single `/health` endpoint*: Fails to distinguish between process alive and readiness to handle ML inference, causing race conditions in load balancers during deployments.

### Consequences
- **Positive**: Zero downtime rolling deployments in orchestrators by ensuring traffic is only routed to fully ready containers.
- **Positive**: Prevents cascading failures when starting up cold containers.

---

## ADR-005: Lifespan Model Initialization and Synthetic Warm-Up

### Context
Loading scikit-learn/joblib pipelines on demand per request introduces catastrophic latency spikes (hundreds of milliseconds). Even after loading, the initial prediction often incurs Python JIT/bytecode compilation and memory allocation overhead.

### Decision
We utilize FastAPI's `lifespan` context manager in `fraud_service.api.app`:
1. The model is loaded once at application startup.
2. An initial synthetic `_warm_up()` transaction is executed through `FraudScorer` before the application enters the ready state.
3. The warmed scorer instance is attached to `app.state.scorer`.

### Alternatives Considered
- *Lazy initialization on the first incoming request*: Leads to first-request tail latency spikes (p99 degradation) for end users.
- *Global module-level model loading*: Makes testing difficult, leaks state across test runs, and prevents parametric testing with custom configuration.

### Consequences
- **Positive**: Predictable, low inference latencies from the very first production request.
- **Positive**: Clean lifecycle management and safe shutdown hooks.
- **Trade-off**: Startup takes a few seconds longer before the readiness probe succeeds.

---

## ADR-006: Multi-Tier Testing Strategy (Unit, Integration, Behavioural)

### Context
Relying solely on unit tests fails to verify model regression and API contracts, while relying solely on end-to-end tests makes CI pipelines slow and flaky.

### Decision
We adopted a three-tier testing strategy with pytest markers:
1. **Unit tests (`pytest -m unit`)**: Fast, in-memory validation of domain entities, feature extraction, allow/review/block policies, configuration validation, and scorer orchestration using test doubles.
2. **Integration tests (`pytest -m integration`)**: API schema contracts, middleware execution, header propagation, and full corpus verification across 20 valid payloads and 50+ malformed payloads.
3. **Behavioural acceptance tests (`pytest -m behavioural`)**: Tests against the real pre-trained model bundle (`models/fraud_xgb_v3.joblib`), verifying:
   - *Invariance*: Variations in whitespace/casing in merchant categories produce identical scores.
   - *Directional Monotonicity*: Higher transaction amounts strictly increase fraud probability scores.
   - *Golden Score Regression*: Output scores match verified golden values in `data/golden_scores_v3.csv` to machine precision (`abs=1e-12`).

### Alternatives Considered
- *Mocking everything*: Fast, but fails to detect silent regressions in scikit-learn pickle deserialization or feature naming drift.
- *Running only end-to-end tests*: Slower execution and difficult failure localization.

### Consequences
- **Positive**: 111 tests pass in ~0.76 seconds with 99% statement coverage and 95.8% branch coverage.
- **Positive**: CI gates catch logic regressions, input edge cases, and model drift reliably.

---

## ADR-007: Non-Root Least-Privilege Containerization & Multi-Stage Builds

### Context
Running containers as `root` is a significant security risk. Furthermore, naive container builds that copy the entire workspace before installing dependencies produce bloated images and invalidate Docker cache layers on every minor code edit.

### Decision
We implemented a two-stage `Dockerfile`:
1. **Builder Stage (`python:3.12-slim`)**: Extracts dependencies from `pyproject.toml`, installs them into an isolated prefix (`/install`), and packages `fraud_service` as a wheel.
2. **Runtime Stage (`python:3.12-slim`)**: Copies only the built wheel and installed packages from the builder stage. Creates a dedicated system user and group `fraud` (UID/GID 999), changes ownership of `/app`, and executes as `USER fraud`.
3. Added native Docker `HEALTHCHECK` querying `/v1/ready`.

### Alternatives Considered
- *Single-stage Dockerfile*: Produces bloated images containing build tools, caches, and requires root permissions.
- *Running as default root user*: Violates enterprise compliance and container security standards (CIS benchmarks).

### Consequences
- **Positive**: Image size reduced from naive base to ~160.6 MB (well below the 450 MB target).
- **Positive**: Source code modifications rebuild in ~17.2s due to dependency layer caching.
- **Positive**: Trivy vulnerability scanning passes cleanly with no unfixed high/critical CVEs.

---

## ADR-008: CI Pipeline, Immutable Artifacts, and SHA Tagging

### Context
Using mutable image tags like `latest` or `dev` in production deployments makes rollbacks unreliable and obscures the link between deployed artifacts and git commits.

### Decision
In `.github/workflows/ci.yml`:
- Parallel validation jobs for `lint` and `test` (with branch coverage gate `>= 80%`).
- Build container image once in `image-smoke`, run container smoke tests and Trivy security scans.
- On merges to `main`, publish the tested container image to GitHub Container Registry (GHCR) using both the immutable Git commit SHA (`ghcr.io/<repo>:<sha>`) and the floating `main` tag.
- Capture and report the immutable image digest (`@sha256:...`) in the CI step summary.

### Alternatives Considered
- *Rebuilding image in publish job*: Violates the "build once, deploy anywhere" principle and introduces potential divergence between tested and published artifacts.
- *Tagging only with `latest`*: Obscures release provenance and prevents deterministic rollbacks.

### Consequences
- **Positive**: Guaranteed provenance, traceability, and reproducibility from git commit to running container.
- **Positive**: Automated branch coverage gating ensures quality standards are maintained.

---

## ADR-009: Centralized Validated Configuration & Privacy-Safe Structured Logging

### Context
Scattered `os.environ.get()` calls lead to runtime crashes due to missing or mistyped environment variables. Unstructured plaintext logs are difficult to parse in log aggregators and risk leaking Personally Identifiable Information (PII) or raw fraud probabilities.

### Decision
- **Configuration**: Implemented `fraud_service.config.Settings` using `pydantic-settings` with `FRAUD_` prefix. Enforces fail-fast startup validation for model file existence and verifies that `review_band_width <= block_threshold`.
- **Structured Logging**: Structured JSON logging (`JsonFormatter`) with correlated `trace_id` retrieved from `contextvars.ContextVar`.
- **Privacy Protection**: Prediction logs emit coarse probability buckets (`"0.00-0.24"`, `"0.25-0.49"`, `"0.50-0.74"`, `"0.75-1.00"`) and decision labels instead of continuous raw floating-point probabilities, preventing reverse engineering and data leakage.

### Alternatives Considered
- *Ad-hoc environment reads*: Prone to silent fallback to defaults and difficult to audit.
- *Standard human-readable text logs*: Hard to index in ELK/Datadog/CloudWatch and prone to leaking raw transaction data.

### Consequences
- **Positive**: Invalid configurations fail immediately at service boot with descriptive error messages.
- **Positive**: Logs are machine-readable, traceable across request lifecycles via `trace_id`, and privacy-compliant.
