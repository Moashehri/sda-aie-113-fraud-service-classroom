"""Shared test fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fraud_service.api.app import create_app
from fraud_service.config import Settings
from fraud_service.domain.entities import FraudFeatures

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "fraud_xgb_v3.joblib"


class FixedModel:
    """Small deterministic model test double."""

    version = "test-v1"

    def __init__(self, probability: float = 0.72) -> None:
        self.probability = probability

    def predict_probability(self, features: FraudFeatures) -> float:
        return self.probability


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        model_path=MODEL_PATH,
        log_level="ERROR",
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    return create_app(settings=settings, model_factory=lambda _: FixedModel())


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client
