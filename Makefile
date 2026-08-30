.PHONY: install run-batch lint

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e ".[dev]"

run-batch:
	$(PYTHON) -m fraud_service.batch

lint:
	$(PYTHON) -m ruff check src tests
