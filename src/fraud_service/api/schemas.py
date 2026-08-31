"""Strict API request and response schemas."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from fraud_service.domain.policies import Decision

Identifier = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    ),
]
TransactionIdentifier = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=10,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    ),
]
MerchantCategory = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 _-]*$",
    ),
]


class PredictRequest(BaseModel):
    """Validated transaction payload accepted by the prediction endpoint."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: TransactionIdentifier
    amount_sar: float = Field(strict=True, gt=0.0, le=1_000_000, allow_inf_nan=False)
    channel: Literal["pos", "ecom", "atm", "transfer"]
    merchant_category: MerchantCategory
    customer_id: Identifier
    timestamp: datetime

    @field_validator("transaction_id", "customer_id", mode="before")
    @classmethod
    def identifiers_must_not_have_outer_whitespace(cls, value: Any) -> Any:
        if isinstance(value, str) and value != value.strip():
            raise ValueError("identifiers must not have leading or trailing whitespace")
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_must_be_iso_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            # Pydantic validators must use ValueError to produce a 422 response.
            raise ValueError("timestamp must be an ISO 8601 string")  # noqa: TRY004
        if "T" not in value:
            raise ValueError("timestamp must include a date and time separator")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("timestamp must be a valid ISO 8601 datetime") from exc
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value


class PredictResponse(BaseModel):
    """Fraud prediction returned to an API client."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    fraud_probability: float = Field(ge=0.0, le=1.0)
    decision: Decision
    model_version: str
    trace_id: str


class StatusResponse(BaseModel):
    """Health or readiness status."""

    status: Literal["ok", "ready"]


class ErrorEnvelope(BaseModel):
    """Consistent response body for request and server errors."""

    error: str
    trace_id: str
    details: dict[str, Any] | list[Any] | None = None
