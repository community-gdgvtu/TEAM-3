"""Ensemble forecast endpoint (SPEC §8).

``POST /ensemble`` takes a compiled Policy DSL (plus optional shocks and a
horizon) and returns the flagship cordon-traffic reduction estimated by three
independent methods (structural agent-based, historical-analogue transfer,
reduced-form elasticity), pooled with documented weights and an explicit
disagreement signal. No LLM touches any number (SPEC §8/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..ensemble.model import run_ensemble
from ..ensemble.schema import EnsembleForecast
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/ensemble", tags=["ensemble"])


class EnsembleRequest(BaseModel):
    """Input to ``POST /ensemble``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to the run."
    )
    horizon_months: float = Field(
        default=24.0,
        ge=0.0,
        description="Horizon for the ensemble estimate; snapped to the nearest "
        "checkpoint at or before this month (default 2 years).",
    )


@router.post("", response_model=EnsembleForecast, summary="Ensemble forecast (SPEC §8)")
def ensemble(req: EnsembleRequest) -> EnsembleForecast:
    """Return the pooled multi-method ensemble forecast for the flagship metric."""
    return run_ensemble(req.policy, shocks=req.shocks, horizon_months=req.horizon_months)
