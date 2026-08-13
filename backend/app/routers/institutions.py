"""Institutional review endpoint (SPEC §18).

``POST /institutions/review`` takes a compiled Policy DSL (plus optional shocks)
and returns assessments from the four institutional agents — Climate,
Implementation, Legal/Constitutional Research, and Auditor — each grounded in the
deterministic simulation's Δ metrics, event ledger and provenance, with a
professional verdict. Numbers come only from the model; no LLM (SPEC §18/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..institutions.review import run_institutional_review
from ..institutions.schema import InstitutionsResponse
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/institutions", tags=["institutions"])


class InstitutionsRequest(BaseModel):
    """Input to ``POST /institutions/review``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL to review.")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors for the simulation."
    )


@router.post(
    "/review",
    response_model=InstitutionsResponse,
    summary="Institutional review panel (SPEC §18)",
)
def institutional_review(req: InstitutionsRequest) -> InstitutionsResponse:
    """Return the four institutional agents' evidence-grounded reviews."""
    return run_institutional_review(req.policy, shocks=req.shocks)
