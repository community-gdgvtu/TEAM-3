"""Simulated media endpoint (ROADMAP M6, SPEC §15).

``POST /media`` takes a compiled Policy DSL and returns clearly-labelled SIMULATED
media coverage: archetype headlines at Month 5 and Year 2, built strictly from
the event ledger, outcome metrics and opinion state. Every artifact carries the
SIMULATED banner and cites the model output it rests on (SPEC §15/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..media import MediaResponse, run_media
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/media", tags=["media"])


class MediaRequest(BaseModel):
    """Input to ``POST /media``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL to generate coverage for.")
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")


@router.post("", response_model=MediaResponse, summary="Generate simulated media coverage")
def media(req: MediaRequest) -> MediaResponse:
    """Return simulated archetype media coverage for ``req.policy``."""
    return run_media(req.policy, shocks=req.shocks)
