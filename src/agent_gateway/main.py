"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from agent_gateway.api.errors import ApiError
from agent_gateway.api.middleware import MetricsMiddleware
from agent_gateway.api.routes import api_error_handler
from agent_gateway.api.routes import router as api_router
from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.errors import (
    http_exception_handler,
    problem_response,
    unhandled_exception_handler,
)
from agent_gateway.middleware.logging import JSONLoggingMiddleware
from agent_gateway.middleware.request_id import RequestIDMiddleware
from agent_gateway.observability.logging import configure_logging
from agent_gateway.observability.tracing import configure_tracing, get_tracer
from agent_gateway.storage.database import check_db_connection, close_db, init_db
from agent_gateway.storage.seed import seed_database

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    tracer = get_tracer()
    with tracer.start_as_current_span("application.startup"):
        logger.info(
            "application_starting",
            app_name=settings.app_name,
            app_env=settings.app_env,
            demo_mode=settings.is_demo,
        )
    await init_db(settings)
    if settings.is_demo:
        await seed_database(settings)
    yield
    await close_db()
    logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.app_name,
        version="0.1.0",
        description=(
            "Enterprise Agent Gateway — governed AI orchestration for "
            "commercial real estate operations."
        ),
        lifespan=lifespan,
        debug=cfg.app_debug,
    )
    app.state.settings = cfg

    app.add_middleware(MetricsMiddleware)
    app.add_middleware(JSONLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)

    app.include_router(api_router)

    @app.get("/health/live", tags=["health"])
    async def health_live() -> dict[str, str]:
        """Liveness probe — process is running."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> dict[str, str | bool]:
        """Readiness probe — dependencies are available."""
        db_ok = True
        if cfg.readiness_db_check:
            db_ok = await check_db_connection(cfg)

        if not db_ok:
            raise HTTPException(status_code=503, detail="Database is not ready")

        return {
            "status": "ok",
            "demo_mode": cfg.is_demo,
            "database": db_ok,
        }

    return app


async def _validation_exception_handler(request, exc: RequestValidationError):
    return problem_response(
        status=422,
        title="Validation Error",
        detail="Request validation failed.",
        type_suffix="validation-error",
        instance=str(request.url.path),
        errors=exc.errors(),
    )


app = create_app()


def run() -> None:
    """Run the application with uvicorn."""
    settings = get_settings()
    configure_logging(settings)
    uvicorn.run(
        "agent_gateway.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_config=None,
    )


if __name__ == "__main__":
    run()
