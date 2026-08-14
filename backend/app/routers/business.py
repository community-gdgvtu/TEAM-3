"""Business View endpoints — follow a single firm (SPEC §17 Business View).

``POST /business`` takes a compiled Policy DSL and either an explicit ``firm_id``
or a ``select`` archetype, and returns that firm's Time-Machine trajectory: its
profile, its World-A operating picture, and how footfall, labour accessibility,
deliveries, costs and a revenue proxy evolve across the horizon — plus the
adaptation decisions its exposure implies and a deterministic "Why?" narrative.
Labour accessibility reuses the same deterministic mode-choice model as
``/simulate``; footfall / deliveries / cost / revenue reuse the same economic
coefficients as ``/economy``; no LLM touches the numeric path (SPEC §34).

``GET /business/sample`` returns a small, diverse, policy-independent set of firms
so a UI can populate a "click a firm" picker.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..business.schema import BusinessView, FirmSample
from ..business.service import (
    _SELECTORS,
    FirmNotFound,
    build_business_view,
    sample_firms,
)
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/business", tags=["business"])


class BusinessRequest(BaseModel):
    """Input to ``POST /business``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    firm_id: str | None = Field(
        default=None,
        description="Explicit synthetic-firm id to profile (overrides `select`).",
    )
    select: str = Field(
        default="representative",
        description=(
            "Archetype to auto-pick when no firm_id is given: "
            "representative | most_exposed | biggest_footfall_loss | pedestrian_winner | largest."
        ),
    )


@router.post(
    "",
    response_model=BusinessView,
    summary="Follow one firm through the Time Machine (SPEC §17 Business View)",
)
def business(req: BusinessRequest) -> BusinessView:
    """Return the Business View for one firm under the policy (SPEC §17)."""
    if req.firm_id is None and req.select not in _SELECTORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown select '{req.select}'. Valid: {', '.join(_SELECTORS)}.",
        )
    try:
        return build_business_view(req.policy, firm_id=req.firm_id, selector=req.select)
    except FirmNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Unknown firm_id: {exc}") from exc


@router.get(
    "/sample",
    response_model=list[FirmSample],
    summary="A diverse set of firms for a 'click a firm' picker (SPEC §17)",
)
def business_sample(limit: int = 6) -> list[FirmSample]:
    """Return a small, deterministic, policy-independent set of firms."""
    return sample_firms(limit=max(1, min(20, limit)))
