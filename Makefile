.PHONY: install run run-batch test lint format image image-naive image-size up \
	smoke loadtest startup-time cache-check compose-config

PYTHON ?= python
IMAGE ?= fraud-service:local
NAIVE_IMAGE ?= fraud-service:naive
COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.yml

install:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	PYTHONPATH=src $(PYTHON) -m fraud_service.api.app

run-batch:
	PYTHONPATH=src $(PYTHON) -m fraud_service.batch

test:
	PYTHONPATH=src $(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests
	$(PYTHON) -m mypy src/fraud_service --strict
	PYTHONPATH=src lint-imports

format:
	$(PYTHON) -m ruff check --fix src tests
	$(PYTHON) -m ruff format src tests

image:
	docker build --file Dockerfile --tag $(IMAGE) .

image-naive:
	docker build --file Dockerfile.naive --tag $(NAIVE_IMAGE) .

image-size:
	docker image inspect $(IMAGE) --format '{{.Size}}' | awk '{printf "%.1f MB\\n", $$1 / 1024 / 1024}'

compose-config:
	$(COMPOSE) --file $(COMPOSE_FILE) config

up:
	$(COMPOSE) --file $(COMPOSE_FILE) up --build --detach

smoke:
	./scripts/smoke.sh

loadtest:
	$(COMPOSE) --file $(COMPOSE_FILE) --profile loadtest run --rm loadtest

startup-time:
	./scripts/startup_time.sh

cache-check:
	./scripts/cache_rebuild.sh
