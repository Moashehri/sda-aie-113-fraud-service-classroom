"""FastAPI route definitions."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from fraud_service.api.schemas import PredictRequest, PredictResponse, StatusResponse
from fraud_service.domain.entities import Transaction
from fraud_service.logging_setup import probability_bucket
from fraud_service.service.scorer import FraudScorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


def get_scorer(request: Request) -> FraudScorer:
    """Return the scorer loaded during application startup."""
    scorer = getattr(request.app.state, "scorer", None)
    if scorer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not ready",
        )
    return scorer


@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    request: Request,
    scorer: FraudScorer = Depends(get_scorer),  # noqa: B008
) -> PredictResponse:
    """Score one validated transaction for fraud."""
    result = scorer.score(
        Transaction(
            transaction_id=payload.transaction_id,
            amount_sar=payload.amount_sar,
            channel=payload.channel,
            merchant_category=payload.merchant_category,
            customer_id=payload.customer_id,
            timestamp=payload.timestamp,
        )
    )

    logger.info(
        "prediction_served",
        extra={
            "event": "prediction_served",
            "decision": result.decision.value,
            "probability_bucket": probability_bucket(result.score),
            "model_version": result.model_version,
        },
    )

    return PredictResponse(
        transaction_id=result.transaction_id,
        fraud_probability=result.score,
        decision=result.decision,
        model_version=result.model_version,
        trace_id=request.state.trace_id,
    )


@router.get("/health", response_model=StatusResponse)
def health() -> StatusResponse:
    """Report process liveness without checking dependencies."""
    return StatusResponse(status="ok")


@router.get("/ready", response_model=StatusResponse)
def ready(request: Request) -> StatusResponse:
    """Report readiness only after the model has loaded."""
    if getattr(request.app.state, "scorer", None) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not ready",
        )
    return StatusResponse(status="ready")
