"""Counterfactual comparison endpoint (ROADMAP M7, SPEC §21).

``POST /compare`` takes a compiled Policy DSL and an optional list of amendments
and returns World A (baseline) vs World B (intervention) vs one world per
amendment (C, D…) in a single payload — each with its Δ-vs-baseline and
Δ-vs-intervention — plus a headline table (baseline + every world + Δ per metric
at one horizon). The baseline is always present (SPEC §21); every number comes
from the deterministic model (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..simulation.amendment import Amendment
from ..simulation.counterfactual import (
    CounterfactualComparison,
    compare_counterfactuals,
)
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    """Input to ``POST /compare``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL — becomes World B.")
    amendments: list[Amendment] = Field(
        default_factory=list,
        description="Structured amendments; each becomes a world C, D… (SPEC §12/§21).",
    )
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the headline table; snapped to nearest checkpoint "
        "(default 5 years).",
    )


@router.post("", response_model=CounterfactualComparison, summary="Compare worlds A/B/C…")
def compare(req: CompareRequest) -> CounterfactualComparison:
    """Return the counterfactual comparison across all requested worlds."""
    return compare_counterfactuals(
        req.policy,
        req.amendments,
        shocks=req.shocks,
        horizon_months=req.horizon_months,
    )
