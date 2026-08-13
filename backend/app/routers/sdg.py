"""SDG alignment endpoint (SPEC §23).

``POST /sdg`` takes a compiled Policy DSL (plus optional exogenous shocks and a
horizon) and returns how the policy maps onto UN SDG targets — core SDG 11
(sustainable cities/transport) and SDG 16 (evidence-informed institutions),
secondary SDG 10 (reduced inequalities) and SDG 13 (climate action). Every
indicator carries its own baseline / scenario / change / data source /
confidence; no arbitrary composite "SDG score" is produced (SPEC §23) and no LLM
touches any number (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..sdg.model import build_sdg_report
from ..sdg.schema import SdgReport
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/sdg", tags=["sdg"])


class SdgRequest(BaseModel):
    """Input to ``POST /sdg``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the indicators; snapped to the nearest checkpoint "
        "(default 5 years).",
    )


@router.post("", response_model=SdgReport, summary="Map a policy onto SDG targets")
def sdg(req: SdgRequest) -> SdgReport:
    """Return the policy's SDG alignment report (SPEC §23)."""
    return build_sdg_report(
        req.policy, shocks=req.shocks, horizon_months=req.horizon_months
    )
