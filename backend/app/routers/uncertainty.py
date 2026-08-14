"""Uncertainty endpoint (ROADMAP M7, SPEC §24).

``POST /uncertainty`` takes a compiled Policy DSL and a metric key and returns a
fan of plausible futures for that metric: Monte-Carlo median + 50/80/95%
intervals per horizon, a ranked list of most-influential assumptions, and a
behavioural-regime ensemble measuring model disagreement. Every number is a
re-run of the deterministic model with perturbed input assumptions — no LLM on
the numeric path (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks
from ..uncertainty import UncertaintyResult, run_uncertainty
from ..uncertainty.engine import MetricNotFound

router = APIRouter(prefix="/uncertainty", tags=["uncertainty"])


class UncertaintyRequest(BaseModel):
    """Input to ``POST /uncertainty``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    metric_key: str = Field(description="Metric to characterise, e.g. 'traffic.daily_vehicle_km'.")
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")
    horizon_months: float | None = Field(
        default=None,
        description="Headline horizon; snapped to the nearest checkpoint. Defaults to 5 years.",
    )
    samples: int = Field(
        default=100, ge=20, le=500, description="Monte-Carlo sample count (clamped 20–500)."
    )
    seed: int = Field(default=12345, description="RNG seed — runs are reproducible.")


@router.post("", response_model=UncertaintyResult, summary="Uncertainty fan for a metric")
def uncertainty(req: UncertaintyRequest) -> UncertaintyResult:
    """Return the Monte-Carlo uncertainty fan + sensitivity for ``req.metric_key``."""
    try:
        return run_uncertainty(
            req.policy,
            req.metric_key,
            shocks=req.shocks,
            horizon_months=req.horizon_months,
            samples=req.samples,
            seed=req.seed,
        )
    except MetricNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": str(exc), "available_metric_keys": exc.available},
        ) from exc
