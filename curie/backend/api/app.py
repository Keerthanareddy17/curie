"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from curie.backend.api.routes.evaluation import router as evaluation_router
from curie.backend.api.routes.health import router as health_router
from curie.backend.api.routes.investigate import router as investigate_router
from curie.backend.api.routes.investigations import router as investigations_router
from curie.shared.config import get_settings
from curie.shared.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    app = FastAPI(
        title="curie",
        description=(
            "An autonomous, evidence-aware biological research agent. "
            "Research and education software only — see docs/LIMITATIONS.md."
        ),
        version="0.1.0",
    )

    # The frontend (a different origin/port in dev, a different domain in
    # production) needs to call this API directly from the browser. Local dev
    # origins are always allowed; the deployed frontend's origin is added via
    # CURIE_CORS_ORIGINS (comma-separated) so the production domain never
    # needs to be hardcoded here.
    extra_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            *extra_origins,
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health_router)  # GET /health
    app.include_router(health_router, prefix="/api")  # GET /api/health
    app.include_router(investigate_router)  # legacy POST /investigate
    app.include_router(investigations_router)  # POST/GET /api/investigations...
    app.include_router(evaluation_router)  # GET /api/evaluation/latest

    return app


app = create_app()
