.PHONY: install run run-batch test lint format image

PYTHON ?= python
IMAGE ?= fraud-service:local

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

format:
	$(PYTHON) -m ruff check --fix src tests
	$(PYTHON) -m ruff format src tests

image:
	docker build --tag $(IMAGE) .
