"""Ports used by the application service layer."""

from typing import Protocol

from fraud_service.domain.entities import FraudFeatures, Transaction


class Model(Protocol):
    """A fraud probability model, independent of any ML framework."""

    @property
    def version(self) -> str:
        """Return the version of the loaded model artefact."""
        ...

    def predict_probability(self, features: FraudFeatures) -> float:
        """Return a fraud probability for one feature vector."""
        ...


class FeatureRepo(Protocol):
    """Port for obtaining model features when an external store is needed."""

    def get_features(self, transaction: Transaction) -> FraudFeatures:
        """Return the features associated with a transaction."""
        ...
