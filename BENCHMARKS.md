# Lab 3 container measurements

All values below must be measured on this machine. Do not replace any
`NOT YET MEASURED` entry with course example values.

## Measurement context

| Item | Value |
| --- | --- |
| Date/time | NOT YET MEASURED |
| Host hardware / RAM | NOT YET MEASURED |
| OS and Docker version | NOT YET MEASURED |
| CPU architecture / platform | NOT YET MEASURED |
| API worker count | 1 (`uvicorn.run` default) |
| Load workload | `LOADTEST_VUS=10`, `LOADTEST_ITERATIONS=500` |
| Request | `POST /v1/predict` using `scripts/loadtest.js` |

## Image builds

| Build | Command | Build time | Image size |
| --- | --- | --- | --- |
| Naive | `make image-naive` | NOT YET MEASURED | NOT YET MEASURED |
| Multi-stage | `make image` | NOT YET MEASURED | NOT YET MEASURED (must be ≤450 MB) |

After each build, record the size from `make image-size` (set `IMAGE` to the
appropriate tag for the naive image).

## Cache discipline

| Check | Command | Result |
| --- | --- | --- |
| Source-changed warm rebuild | `make cache-check` | NOT YET MEASURED (must be <30 s) |
| Dependency layer cache hit | `make cache-check` | NOT YET MEASURED |

`cache_rebuild.sh` performs its one-line `routes.py` change only in a temporary
build context, never in the working tree.

## Startup readiness

| Check | Command | Time to ready |
| --- | --- | --- |
| Compose API readiness | `make startup-time` | NOT YET MEASURED |

The script starts Compose and polls `/v1/ready`; it fails on timeout instead of
reporting container creation as success.

## Load-test comparison

| Environment | p99 latency | VUs | Iterations | Workers | Notes |
| --- | --- | --- | --- | --- | --- |
| Lab 2 bare metal | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | Record the comparable original run. |
| Lab 3 container | NOT YET MEASURED | 10 | 500 | 1 | Run `make loadtest`; record k6 `http_req_duration` p(99). |

Compare only runs with matching workload, concurrency, worker count, and host
platform. If those differ, document the difference rather than treating the
numbers as directly comparable.
