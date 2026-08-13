"""Public-reaction endpoint (ROADMAP M6, SPEC §13).

``POST /public`` takes a compiled Policy DSL and returns the cohort opinion
distribution (income band × geography × travel mode) plus the overall split
across the six SPEC §13 buckets. Deterministic and Simulated (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..opinion import PublicOpinion, compute_public_opinion
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/public", tags=["public"])


class PublicRequest(BaseModel):
    """Input to ``POST /public``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL to gauge reaction to.")


@router.post("", response_model=PublicOpinion, summary="Cohort public reaction")
def public(req: PublicRequest) -> PublicOpinion:
    """Return the deterministic cohort opinion distribution for ``req.policy``."""
    return compute_public_opinion(req.policy)
