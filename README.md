# fraud-service

A classroom fraud-scoring service built with a clean Python `src` layout. The
domain and service layers are framework-independent; FastAPI and scikit-learn
are isolated at the edges.

## Setup and commands

Python 3.12 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

The Makefile is the operational interface:

```bash
make run        # API on http://localhost:8000
make run-batch  # write scored.csv for all 5,000 sample rows
make test       # unit, integration, and behavioural tests
make lint       # Ruff lint and formatting checks
make image      # build fraud-service:local
```

The API exposes `POST /v1/predict`, `GET /v1/health`, and `GET /v1/ready`.

## Configuration

All settings use the `FRAUD_` prefix. Copy `configs/settings.example.env` to
`.env` for local overrides. The committed example contains safe values only;
`.env` files are ignored by Git and Docker.

## Architecture

- `domain/` contains entities, deterministic feature extraction, and policies.
- `service/` coordinates use cases through framework-neutral protocols.
- `adapters/` implements infrastructure ports, including the joblib model.
- `api/` validates HTTP data and composes the application at startup.
- `config.py` and `logging_setup.py` centralize operational concerns.

Model artefacts in `models/` are versioned application inputs. They are not
source code, and only the sklearn adapter knows how to load or execute them.
