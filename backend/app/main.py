"""URBAN backend application entrypoint.

Run locally with::

    uvicorn app.main:app --reload

This is the M0 skeleton: a FastAPI app with CORS and a ``/health`` probe.
Simulation, policy-compiler and parliament routers are added in later milestones.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import baseline, health, policy, simulate


def create_app() -> FastAPI:
    """Application factory so tests can build isolated instances."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "Policy digital twin backend. Every quantitative output is tagged "
            "Observed/Estimated/Simulated/Generated; LLMs never generate core "
            "numeric effects (SPEC §34)."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(policy.router)
    app.include_router(baseline.router)
    app.include_router(simulate.router)

    @app.get("/", tags=["system"], summary="Service root")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
