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
    assumptions,
    backtest,
    baseline,
    brief,
    business,
    capabilities,
    citizen,
    compare,
    datafabric,
    diffusion,
    dynamics,
    economy,
    ensemble,
    evidence,
    health,
    institutions,
    media,
    microsim,
    northstar,
    optimise,
    parliament,
    policy,
    press,
    public,
    registry,
    reproduce,
    robustness,
    run,
    scenarios,
    sdg,
    sensitivity,
    simulate,
    spatial,
    stress,
    timeseries,
    uncertainty,
    world,
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
    app.include_router(capabilities.router)
    app.include_router(policy.router)
    app.include_router(baseline.router)
    app.include_router(simulate.router)
    app.include_router(parliament.router)
    app.include_router(public.router)
    app.include_router(media.router)
    app.include_router(evidence.router)
    app.include_router(uncertainty.router)
    app.include_router(sensitivity.router)
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
    app.include_router(datafabric.router)
    app.include_router(assumptions.router)
    app.include_router(world.router)
    app.include_router(citizen.router)
    app.include_router(business.router)
    app.include_router(run.router)
    app.include_router(northstar.router)
    app.include_router(brief.router)
    app.include_router(robustness.router)
    app.include_router(scenarios.router)

    @app.get("/", tags=["system"], summary="Service root")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "health": "/health",
            "capabilities": "/capabilities",
            "scenarios": "/scenarios",
        }

    return app


app = create_app()
