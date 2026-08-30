"""FastAPI route definitions."""

from fastapi import APIRouter, Depends, HTTPException, Request

from fraud_service.api.schemas import PredictRequest, PredictResponse
from fraud_service.domain.entities import Transaction
from fraud_service.service.scorer import FraudScorer

router = APIRouter(prefix="/v1")


def get_scorer(request: Request) -> FraudScorer:
    """Dependency to get the loaded scorer from application state."""
    scorer = getattr(request.app.state, "scorer", None)
    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service Unavailable", "message": "Model is still loading or failed to load."}
        )
    return scorer


@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    request: Request,
    scorer: FraudScorer = Depends(get_scorer),  # noqa: B008
) -> PredictResponse:
    """Score a transaction for fraud."""
    transaction = Transaction(
        transaction_id=payload.transaction_id,
        amount_sar=payload.amount_sar,
        channel=payload.channel,
        merchant_category=payload.merchant_category,
        customer_id=payload.customer_id,
        timestamp=payload.timestamp,
    )
    
    scored_txn = scorer.score(transaction)
    
    # Retrieve trace_id from request state, set by middleware
    trace_id = getattr(request.state, "trace_id", "unknown")

    return PredictResponse(
        transaction_id=scored_txn.transaction_id,
        fraud_probability=scored_txn.score,
        decision=scored_txn.decision,
        model_version=scored_txn.model_version,
        trace_id=trace_id,
    )


@router.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check. Always returns 200 OK if the API is running."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    """Readiness check. Returns 200 OK only if the model is fully loaded."""
    if getattr(request.app.state, "scorer", None) is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ready"}
