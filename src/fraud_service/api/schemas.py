"""API schemas for validation and serialization."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fraud_service.domain.policies import Decision


class PredictRequest(BaseModel):
    """Payload for scoring a transaction."""
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(..., min_length=1, max_length=100)
    amount_sar: float = Field(..., ge=0.0, description="Amount must not be negative")
    channel: str = Field(..., min_length=1, max_length=50)
    merchant_category: str = Field(..., min_length=1, max_length=100)
    customer_id: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime


class PredictResponse(BaseModel):
    """Response containing the fraud score and decision."""
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    fraud_probability: float
    decision: Decision
    model_version: str
    trace_id: str


class ErrorEnvelope(BaseModel):
    """Standardized error response."""
    error: str
    trace_id: str
    details: dict[str, Any] | None = None
