"""Framework-free domain objects and feature extraction."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import log1p
from typing import Any

from fraud_service.domain.policies import Decision


@dataclass(frozen=True, slots=True)
class Transaction:
    """The transaction data needed to calculate a fraud score."""

    transaction_id: str
    amount_sar: float
    channel: str
    merchant_category: str
    customer_id: str
    timestamp: datetime

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "Transaction":
        """Create a transaction from a CSV- or request-like mapping."""
        timestamp = values["timestamp"]
        if not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(str(timestamp))

        return cls(
            transaction_id=str(values["transaction_id"]),
            amount_sar=float(values["amount_sar"]),
            channel=str(values["channel"]),
            merchant_category=str(values["merchant_category"]),
            customer_id=str(values["customer_id"]),
            timestamp=timestamp,
        )


@dataclass(frozen=True, slots=True)
class FraudFeatures:
    """Features expected by the trained model."""

    amount_log: float
    channel: str
    mcc: str
    hour_of_day: int
    is_night: int

    def as_mapping(self) -> dict[str, float | str | int]:
        """Return features with the model's training-time column names."""
        return {
            "amount_log": self.amount_log,
            "channel": self.channel,
            "mcc": self.mcc,
            "hour_of_day": self.hour_of_day,
            "is_night": self.is_night,
        }


@dataclass(frozen=True, slots=True)
class ScoredTransaction:
    """A model score combined with the business decision."""

    transaction_id: str
    score: float
    decision: Decision
    model_version: str


def extract_features(transaction: Transaction) -> FraudFeatures:
    """Deterministically derive the model features for one transaction."""
    hour = transaction.timestamp.hour
    return FraudFeatures(
        amount_log=log1p(transaction.amount_sar),
        channel=transaction.channel,
        mcc=transaction.merchant_category.strip().upper().replace(" ", "_"),
        hour_of_day=hour,
        is_night=int(hour < 6),
    )
