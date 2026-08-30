"""Adapter for the persisted scikit-learn model bundle."""

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from fraud_service.domain.entities import FraudFeatures


class SklearnModel:
    """Load and expose the course's joblib/sklearn model bundle."""

    def __init__(self, pipeline: Pipeline, version: str) -> None:
        self._pipeline = pipeline
        self._version = version

    @property
    def version(self) -> str:
        return self._version

    @classmethod
    def load(cls, path: str | Path) -> "SklearnModel":
        bundle: dict[str, Any] = joblib.load(path)
        return cls(pipeline=bundle["pipeline"], version=str(bundle["version"]))

    def predict_probability(self, features: FraudFeatures) -> float:
        frame = pd.DataFrame([features.as_mapping()])
        return float(self._pipeline.predict_proba(frame)[0, 1])
