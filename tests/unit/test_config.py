"""Tests for centralized configuration validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fraud_service.config import Settings

pytestmark = pytest.mark.unit


def test_missing_model_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="model artefact does not exist"):
        Settings(_env_file=None, model_path=tmp_path / "missing.joblib")


def test_review_band_cannot_exceed_block_threshold() -> None:
    with pytest.raises(ValidationError, match="review_band_width"):
        Settings(
            _env_file=None,
            model_path=Path("models/fraud_xgb_v3.joblib"),
            block_threshold=0.1,
            review_band_width=0.2,
        )
