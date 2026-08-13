"""Citizen View endpoints — follow a single household (SPEC §17 / §31).

``POST /citizen`` takes a compiled Policy DSL and either an explicit ``agent_id``
or a ``select`` archetype, and returns that household's Time-Machine trajectory:
their profile, their World-A commute / transport cost, and how both (plus their
policy support, SPEC §31 Agent State) evolve across the horizon — with a
deterministic "Why?" narrative. Every number reuses the same deterministic
mode-choice model as ``/simulate`` and the same per-agent opinion model as
``/public``; no LLM touches the numeric path (SPEC §34).

``GET /citizen/sample`` returns a small, diverse, policy-independent set of
households so a UI can populate a "click a household" picker.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..citizen.schema import CitizenSample, CitizenView
from ..citizen.service import (
    CitizenNotFound,
    _SELECTORS,
    build_citizen_view,
    sample_citizens,
)
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/citizen", tags=["citizen"])


class CitizenRequest(BaseModel):
    """Input to ``POST /citizen``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    agent_id: str | None = Field(
        default=None,
        description="Explicit synthetic-agent id to profile (overrides `select`).",
    )
    select: str = Field(
        default="representative",
        description=(
            "Archetype to auto-pick when no agent_id is given: "
            "representative | most_burdened | biggest_loser | biggest_winner | median."
        ),
    )


@router.post(
    "",
    response_model=CitizenView,
    summary="Follow one household through the Time Machine (SPEC §17/§31)",
)
def citizen(req: CitizenRequest) -> CitizenView:
    """Return the Citizen View for one household under the policy (SPEC §17/§31)."""
    if req.agent_id is None and req.select not in _SELECTORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown select '{req.select}'. Valid: {', '.join(_SELECTORS)}.",
        )
    try:
        return build_citizen_view(req.policy, agent_id=req.agent_id, selector=req.select)
    except CitizenNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Unknown agent_id: {exc}") from exc


@router.get(
    "/sample",
    response_model=list[CitizenSample],
    summary="A diverse set of households for a 'click a household' picker (SPEC §17)",
)
def citizen_sample(limit: int = 6) -> list[CitizenSample]:
    """Return a small, deterministic, policy-independent set of households."""
    return sample_citizens(limit=max(1, min(20, limit)))
