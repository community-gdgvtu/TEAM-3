"""Global sensitivity ("tornado") endpoint (SPEC §24/§26).

``POST /sensitivity`` takes a compiled Policy DSL and returns, at one horizon, a
one-at-a-time sensitivity tornado for **every** headline metric plus a global
ranking of which assumptions the answer rests on. Where ``/uncertainty`` gives a
Monte-Carlo fan for a *single* metric, this gives the cheap, deterministic,
cross-metric attribution a decision-maker needs ("if you only pin two numbers,
pin these"). Every value is a re-run of the deterministic model at documented
assumption edges — no LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..sensitivity import SensitivityResult, run_sensitivity
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/sensitivity", tags=["sensitivity"])


class SensitivityRequest(BaseModel):
    """Input to ``POST /sensitivity``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the tornado; snapped to the nearest checkpoint. Defaults to 5 years.",
    )
    metric_keys: list[str] | None = Field(
        default=None,
        description="Optional subset of headline metric keys to analyse; defaults to all.",
    )


@router.post("", response_model=SensitivityResult, summary="Global sensitivity tornado")
def sensitivity(req: SensitivityRequest) -> SensitivityResult:
    """Return the cross-metric one-at-a-time sensitivity tornado (SPEC §24/§26)."""
    return run_sensitivity(
        req.policy,
        shocks=req.shocks,
        horizon_months=req.horizon_months,
        metric_keys=req.metric_keys,
    )
