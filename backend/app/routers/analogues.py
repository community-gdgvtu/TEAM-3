"""Historical Analogue / Causal Layer endpoint (SPEC §7.1).

``POST /analogues`` takes a compiled Policy DSL and estimates the flagship
cordon-traffic effect from *comparable real-world schemes* (London, Stockholm,
Singapore, Milan, Gothenburg, Oslo, Ghent, Madrid) via a difference-in-differences
read transferred by an auditable similarity score, plus a confidence interval,
analogue-quality rating, identification diagnostics and an optional cross-check
against the agent-based model. Historical outcomes are Observed (illustrative);
the transferred estimate is Estimated. No LLM touches any number (SPEC §7.1/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..analogues.model import run_analogues
from ..analogues.schema import AnalogueEstimate, HistoricalCase
from ..analogues.cases import CASES
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/analogues", tags=["analogues"])


class AnalogueRequest(BaseModel):
    """Input to ``POST /analogues``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    horizon_months: float = Field(
        default=24.0,
        ge=0.0,
        description="Horizon for the structural cross-check; snapped to the nearest "
        "checkpoint at or before this month (default 2 years).",
    )
    include_structural_comparison: bool = Field(
        default=True,
        description="Cross-check the analogue estimate against the agent-based model (SPEC §8).",
    )


@router.post("", response_model=AnalogueEstimate, summary="Historical analogue / causal layer (SPEC §7.1)")
def analogues(req: AnalogueRequest) -> AnalogueEstimate:
    """Return the transfer-weighted historical-analogue estimate for a policy."""
    return run_analogues(
        req.policy,
        horizon_months=req.horizon_months,
        include_structural_comparison=req.include_structural_comparison,
    )


@router.get(
    "/cases",
    response_model=list[HistoricalCase],
    summary="The historical-analogue case database (SPEC §7.1)",
)
def cases() -> list[HistoricalCase]:
    """Return the raw curated database of real-world schemes (illustrative, Observed)."""
    return CASES
