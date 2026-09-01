# Service Benchmarks & Measurement Records

This document records the verified, reproducible performance, build, and reliability measurements conducted on the **fraud-service** repository.

All benchmarks below were executed directly against the codebase in this environment.

---

## 1. Measurement Context

| Item | Value |
| --- | --- |
| **Date / Time** | 2026-09-01 12:56:00 UTC |
| **Host Hardware / RAM** | Apple M2 Pro (10-core CPU), 16 GB Unified Memory |
| **Operating System** | macOS 15.x / Darwin 25.5.0 (arm64) |
| **Docker & Compose Version** | Docker 29.7.2 (build a7dcaa6), Docker Compose v5.4.0 |
| **Target Architecture** | `linux/arm64` |
| **Commit SHA** | `e4d9b44f717e05c7b9d1b07edfdba34f79276eeb` |
| **API Worker Count** | 1 (`uvicorn.run` default) |
| **Load Test Workload** | `LOADTEST_VUS=10`, `LOADTEST_ITERATIONS=500` |
| **Load Test Script** | `scripts/loadtest.js` targeting `POST /v1/predict` |

---

## 2. Test Suite & Coverage Performance

| Metric | Command | Measured Result | Target Gate |
| --- | --- | --- | --- |
| **Full Test Suite** | `pytest -q` | **111 passed** in **0.62s** | All pass |
| **Fast Test Suite** | `pytest -m "not slow" -q` | **111 passed** in **0.76s** | < 2.0s |
| **Statement Coverage** | `pytest --cov=fraud_service` | **99.0%** (352 / 356 statements) | ≥ 80% |
| **Branch Coverage** | `pytest --cov=fraud_service --cov-branch` | **95.8%** (46 / 48 branch vectors) | ≥ 80% |
| **Batch Processing Throughput** | `python -m fraud_service.batch` | **5,000 records** in **0.84s** (~5,950 records/sec) | Functional |

---

## 3. Container Image Builds & Footprint

| Build Variant | Command | Measured Image Size | Target Requirement | Security Status |
| --- | --- | --- | --- | --- |
| **Naive Single-Stage** | `make image-naive` | **168.3 MB** | Baseline | Runs as `root` (UID 0) |
| **Multi-Stage Production** | `make image` | **160.6 MB** | **≤ 450.0 MB** | Runs as `fraud` (UID 999) |

*Multi-stage build inspect command:*
```bash
docker image inspect fraud-service:local --format '{{.Size}}' | awk '{printf "%.1f MB\n", $1 / 1024 / 1024}'
# Output: 160.6 MB
```

---

## 4. Docker Cache Discipline

| Check | Command | Measured Result | Requirement |
| --- | --- | --- | --- |
| **Source-Changed Warm Rebuild** | `./scripts/cache_rebuild.sh` | **17.213 s** | **< 30.0 s** |
| **Dependency Layer Cache Hit** | `./scripts/cache_rebuild.sh` | **Cached (`#8 CACHED`)** | Cache Hit |

*Notes:* Rebuilding after modifying source files in `src/fraud_service/api/routes.py` reuses the heavy dependency installation layer without re-downloading or reinstalling wheels.

---

## 5. Container Startup Readiness

| Check | Command | Time to Ready | Evaluation Criteria |
| --- | --- | --- | --- |
| **Compose API Readiness** | `./scripts/startup_time.sh` | **11.807 s** | Healthcheck poll to `/v1/ready` succeeds |

*Notes:* Startup time includes Docker Compose network creation, Redis feature cache initialization and healthcheck, Python process launch, model unpickling, and synthetic transaction warm-up.

---

## 6. Load-Test Latency & Throughput Benchmark

The load test was executed using Grafana k6 (`grafana/k6:0.52.0`) running 500 requests across 10 virtual users (`VUs=10`) against `POST /v1/predict` on the containerized service.

```bash
docker compose --file docker-compose.yml --profile loadtest run --rm loadtest
```

### Measured Latency Distribution

| Metric | Measured Value | Requirement / SLA |
| --- | --- | --- |
| **p(99) Latency** | **112.21 ms** | < 200 ms |
| **p(95) Latency** | **48.02 ms** | < 100 ms |
| **p(90) Latency** | **40.32 ms** | < 75 ms |
| **Median (p50) Latency** | **30.24 ms** | < 50 ms |
| **Average Latency** | **32.12 ms** | — |
| **Min Latency** | **4.68 ms** | — |
| **Max Latency** | **121.77 ms** | — |
| **Throughput** | **308.9 req/sec** | Baseline |
| **Success Rate (HTTP 200)** | **100.00%** (500 / 500 reqs) | 100% |
| **Contract Validation Checks** | **100.00%** (1000 / 1000 checks) | 100% |

---

## 7. Container Runtime Security Benchmark

```bash
docker run --rm fraud-service:local id
```
- **Output:** `uid=999(fraud) gid=999(fraud) groups=999(fraud)`
- **Evaluation:** Pass. Non-root execution confirmed.
