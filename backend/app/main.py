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
from .routers import (
    analogues,
    backtest,
    baseline,
    compare,
    diffusion,
    dynamics,
    economy,
    ensemble,
    evidence,
    health,
    institutions,
    media,
    microsim,
    optimise,
    parliament,
    policy,
    press,
    public,
    registry,
    reproduce,
    sdg,
    simulate,
    spatial,
    stress,
    timeseries,
    uncertainty,
)


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
    app.include_router(parliament.router)
    app.include_router(public.router)
    app.include_router(media.router)
    app.include_router(evidence.router)
    app.include_router(uncertainty.router)
    app.include_router(compare.router)
    app.include_router(optimise.router)
    app.include_router(backtest.router)
    app.include_router(sdg.router)
    app.include_router(diffusion.router)
    app.include_router(registry.router)
    app.include_router(reproduce.router)
    app.include_router(press.router)
    app.include_router(ensemble.router)
    app.include_router(institutions.router)
    app.include_router(economy.router)
    app.include_router(dynamics.router)
    app.include_router(spatial.router)
    app.include_router(microsim.router)
    app.include_router(stress.router)
    app.include_router(analogues.router)
    app.include_router(timeseries.router)

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
