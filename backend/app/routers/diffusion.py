"""Opinion-diffusion endpoint (SPEC §14).

``POST /diffusion`` takes a compiled Policy DSL (plus optional exogenous shocks,
a round count and information shocks) and returns a deterministic Friedkin–Johnsen
opinion-diffusion run over an abstract social graph: per-node opinion
trajectories, issue salience, polarisation, and the coalitions that form —
seeded from the cohort-opinion model, no LLM (SPEC §14/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..diffusion.model import run_diffusion
from ..diffusion.schema import DiffusionResult, InfoShock
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/diffusion", tags=["diffusion"])


class DiffusionRequest(BaseModel):
    """Input to ``POST /diffusion``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to the seed opinions."
    )
    rounds: int = Field(
        default=12, ge=1, le=60, description="Information-diffusion rounds to simulate."
    )
    info_shocks: list[InfoShock] = Field(
        default_factory=list,
        description="Optional narrative shocks (round, node, delta) — e.g. a scandal.",
    )


@router.post("", response_model=DiffusionResult, summary="Simulate opinion diffusion")
def diffusion(req: DiffusionRequest) -> DiffusionResult:
    """Run the opinion-diffusion process for the supplied policy (SPEC §14)."""
    return run_diffusion(
        req.policy,
        shocks=req.shocks,
        rounds=req.rounds,
        info_shocks=req.info_shocks or None,
    )
