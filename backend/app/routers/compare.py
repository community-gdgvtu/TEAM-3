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
    compare_grand,
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


class GrandCompareRequest(BaseModel):
    """Input to ``POST /compare/grand`` — the canonical §21 A/B/C/D comparison."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL — becomes World B.")
    amendment: Amendment | None = Field(
        default=None,
        description="World C — opposition amendment. If omitted, a deterministic "
        "default is derived from the policy (equity-first, SPEC §21).",
    )
    objective: dict = Field(
        default_factory=dict,
        description="Optimiser objective for World D, e.g. "
        "{'reduce_transport_emissions_pct': 20} (SPEC §22).",
    )
    constraints: dict = Field(
        default_factory=dict,
        description="Optimiser constraints for World D, e.g. "
        "{'max_low_income_burden_increase_pct': 2} (SPEC §22).",
    )
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the headline table; snapped to nearest checkpoint "
        "(default 5 years).",
    )


@router.post(
    "/grand",
    response_model=CounterfactualComparison,
    summary="Canonical A/B/C/D comparison (baseline / policy / opposition / optimised)",
)
def compare_grand_endpoint(req: GrandCompareRequest) -> CounterfactualComparison:
    """Return the §21 four-way comparison, composing World C/D deterministically."""
    return compare_grand(
        req.policy,
        amendment=req.amendment,
        objective=req.objective,
        constraints=req.constraints,
        shocks=req.shocks,
        horizon_months=req.horizon_months,
    )
