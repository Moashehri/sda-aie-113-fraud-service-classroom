"""FastAPI application factory and middleware."""

import logging
import secrets
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.routes import router
from fraud_service.api.schemas import ErrorEnvelope
from fraud_service.domain.entities import Transaction
from fraud_service.service.scorer import FraudScorer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # Load model and initialize scorer
    # In a real setup, path would come from settings. Hardcoding for Lab 2.
    model_path = "models/fraud_xgb_v3.joblib"
    model = SklearnModel.load(model_path)
    scorer = FraudScorer(model)
    
    # Warm up prediction to avoid cold start latency
    from datetime import datetime
    dummy_txn = Transaction(
        transaction_id="warmup-01",
        amount_sar=100.0,
        channel="web",
        merchant_category="test",
        customer_id="system",
        timestamp=datetime.now(UTC),
    )
    scorer.score(dummy_txn)
    
    app.state.scorer = scorer
    
    yield
    
    # Cleanup on shutdown
    app.state.scorer = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fraud Scoring API",
        description="Predicts the probability of fraud for a transaction.",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    app.include_router(router)
    
    # Global exception handler for uncaught exceptions (prevents stack traces)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.error(f"Unhandled exception: {exc}")
        error_envelope = ErrorEnvelope(
            error="Internal Server Error",
            trace_id=trace_id,
        )
        return JSONResponse(status_code=500, content=error_envelope.model_dump())

    # Validation exception handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unknown")
        error_envelope = ErrorEnvelope(
            error="Validation Error",
            trace_id=trace_id,
            details={"errors": exc.errors()}
        )
        return JSONResponse(status_code=422, content=error_envelope.model_dump())

    @app.middleware("http")
    async def trace_and_timing_middleware(request: Request, call_next):
        """Inject trace_id and record timing for every request."""
        # Generate trace ID and store in request state
        trace_id = secrets.token_hex(8)
        request.state.trace_id = trace_id
        
        start_time = time.perf_counter()
        
        # Process the request
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        
        # Add headers to response
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

    return app


app = create_app()
