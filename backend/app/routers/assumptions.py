"""Change-assumptions-and-rerun endpoint (SPEC §34.10).

``GET /assumptions`` publishes the catalogue of overridable model assumptions
(the same knobs the §24 uncertainty engine sweeps, read live from the code).

``POST /assumptions/rerun`` takes a compiled Policy DSL plus a set of assumption
overrides, re-runs the deterministic World-A/World-B/Δ pipeline with those
assumptions pinned, and returns a per-metric contrast against the
default-assumption run — SPEC §34's tenth guardrail ("users can change
assumptions and rerun") made concrete. No new numeric model, no LLM (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..assumptions import (
    AssumptionCard,
    AssumptionRerunResult,
    list_assumptions,
    rerun_with_assumptions,
)
from ..assumptions.service import UnknownAssumption
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/assumptions", tags=["assumptions"])


class AssumptionCatalogue(BaseModel):
    """The set of assumptions a user may override and rerun."""

    note: str = Field(
        default=(
            "Overridable input assumptions (Estimated). Pin any to a value in "
            "[low, high] and POST /assumptions/rerun to re-run the deterministic "
            "model (SPEC §34.10). These are the same knobs the §24 uncertainty "
            "engine sweeps, so the two never disagree."
        )
    )
    count: int
    assumptions: list[AssumptionCard]


class RerunRequest(BaseModel):
    """Input to ``POST /assumptions/rerun``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    overrides: dict[str, float] = Field(
        description="Map of assumption name → value. Names from GET /assumptions.",
    )
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon for the contrast; snapped to the nearest checkpoint. "
        "Defaults to Year 2.",
    )


@router.get("", response_model=AssumptionCatalogue, summary="Overridable assumptions")
def catalogue() -> AssumptionCatalogue:
    """List the overridable model assumptions (live from the code)."""
    cards = list_assumptions()
    return AssumptionCatalogue(count=len(cards), assumptions=cards)


@router.post(
    "/rerun",
    response_model=AssumptionRerunResult,
    summary="Change assumptions and rerun → A/B/Δ + contrast",
)
def rerun(req: RerunRequest) -> AssumptionRerunResult:
    """Re-run A/B/Δ with the supplied assumption overrides (SPEC §34.10)."""
    try:
        return rerun_with_assumptions(
            req.policy,
            req.overrides,
            shocks=req.shocks,
            horizon_months=req.horizon_months,
        )
    except UnknownAssumption as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": str(exc), "overridable_assumptions": exc.available},
        ) from exc
