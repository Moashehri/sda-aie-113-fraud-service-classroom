"""FastAPI application factory and composition root."""

import logging
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fraud_service.adapters.sklearn_model import SklearnModel
from fraud_service.api.routes import router
from fraud_service.api.schemas import ErrorEnvelope
from fraud_service.config import Settings, get_settings
from fraud_service.domain.entities import Transaction
from fraud_service.logging_setup import configure_logging, trace_id_context
from fraud_service.service.interfaces import Model
from fraud_service.service.scorer import FraudScorer

logger = logging.getLogger(__name__)
ModelFactory = Callable[[Path], Model]


def _warm_up(scorer: FraudScorer) -> None:
    """Run one synthetic prediction so the first client avoids cold-start cost."""
    scorer.score(
        Transaction(
            transaction_id="warmup-01",
            amount_sar=100.0,
            channel="web",
            merchant_category="test",
            customer_id="system",
            timestamp=datetime.now(UTC),
        )
    )


def _lifespan(
    settings: Settings, model_factory: ModelFactory
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    # pyrefly: ignore [deprecated]
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logger.info("model_loading", extra={"event": "model_loading"})

        model = model_factory(settings.model_path)
        scorer = FraudScorer(
            model=model,
            block_threshold=settings.block_threshold,
            review_band_width=settings.review_band_width,
        )
        _warm_up(scorer)
        app.state.scorer = scorer
        logger.info(
            "model_ready",
            extra={"event": "model_ready", "model_version": model.version},
        )

        try:
            yield
        finally:
            app.state.scorer = None
            logger.info("service_stopped", extra={"event": "service_stopped"})

    return lifespan


def create_app(
    settings: Settings | None = None,
    model_factory: ModelFactory = SklearnModel.load,
) -> FastAPI:
    """Create an independently configurable FastAPI application."""
    app_settings = settings or get_settings()
    application = FastAPI(
        title=app_settings.app_name,
        description="Scores transactions using a versioned fraud model.",
        version="0.1.0",
        lifespan=_lifespan(app_settings, model_factory),
    )
    application.state.scorer = None
    application.state.settings = app_settings
    application.include_router(router)

    @application.middleware("http")
    async def trace_and_timing_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_id = secrets.token_hex(8)
        request.state.trace_id = trace_id
        token = trace_id_context.set(trace_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            duration_ms = (time.perf_counter() - started) * 1_000
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 3),
                    "status_code": status_code,
                },
            )
            trace_id_context.reset(token)

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time"] = f"{duration_ms / 1_000:.6f}"
        return response

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unknown")
        envelope = ErrorEnvelope(
            # pyrefly: ignore [unnecessary-type-conversion]
            error=str(exc.detail),
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope.model_dump(),
            headers={"X-Trace-Id": trace_id},
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unknown")
        errors = [
            {
                "location": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        envelope = ErrorEnvelope(
            error="Validation Error",
            trace_id=trace_id,
            details={"errors": jsonable_encoder(errors)},
        )
        return JSONResponse(
            status_code=422,
            content=envelope.model_dump(),
            headers={"X-Trace-Id": trace_id},
        )

    @application.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.error(
            "unhandled_exception",
            extra={
                "event": "unhandled_exception",
                "exception_type": type(exc).__name__,
                "trace_id": trace_id,
            },
        )
        envelope = ErrorEnvelope(
            error="Internal Server Error",
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=500,
            content=envelope.model_dump(),
            headers={"X-Trace-Id": trace_id},
        )

    return application


app = create_app()


def main() -> None:
    """Run the API using the centralized host and port settings."""
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()
