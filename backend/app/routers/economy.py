"""Economic spillover endpoint (SPEC §7.4).

``POST /economy`` takes a compiled Policy DSL (plus optional exogenous shocks and
a horizon) and returns the policy's local-economy spillover: transparent
input-output / elasticity channels (charge transfer, revenue recycling, CBD
footfall, business logistics, commuter travel cost), per-sector exposure, and a
net partial-equilibrium annual estimate with a band.

The physical drivers (mode shifts, cordon revenue, travel-cost changes) are
Simulated by the deterministic mode-choice model; the monetary translation is
Estimated (SPEC §8). No LLM touches any number (SPEC §34). The report is explicit
about the effects it does not model (``not_modelled``).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..economy.model import build_economic_spillover
from ..economy.schema import EconomicSpilloverReport
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/economy", tags=["economy"])


class EconomyRequest(BaseModel):
    """Input to ``POST /economy``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the estimate; snapped to the nearest checkpoint "
        "(default 5 years). Confidence widens with the horizon.",
    )


@router.post("", response_model=EconomicSpilloverReport,
             summary="Estimate a policy's local economic spillover")
def economy(req: EconomyRequest) -> EconomicSpilloverReport:
    """Return the policy's economic spillover report (SPEC §7.4)."""
    return build_economic_spillover(
        req.policy, shocks=req.shocks, horizon_months=req.horizon_months
    )
