"""Run reproducibility endpoint (SPEC §32).

``POST /reproduce`` takes the same inputs as ``POST /simulate`` (a compiled
Policy DSL, plus optional shocks and seed) and returns the full **reproducibility
manifest** behind SPEC §32's "REPRODUCE RUN" affordance: dataset versions, model
versions, parameters/assumptions, seed, policy DSL, code version and timestamp,
plus a content-addressed ``run_id`` (stable for identical inputs) and a
self-verified ``output_digest`` proving the deterministic core reproduces
byte-for-byte. Deterministic, no LLM (SPEC §32/§34).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..reproduce.manifest import build_manifest
from ..reproduce.schema import ReproManifest
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/reproduce", tags=["reproduce"])


class ReproduceRequest(BaseModel):
    """Input to ``POST /reproduce`` — mirrors the /simulate run request."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Optional[Shocks] = Field(
        default=None, description="Optional exogenous stressors (part of the run identity)."
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed; echoed and hashed for §32 even though the core is deterministic.",
    )


@router.post("", response_model=ReproManifest, summary="Reproducibility manifest for a run (SPEC §32)")
def reproduce(req: ReproduceRequest) -> ReproManifest:
    """Return the content-addressed reproducibility manifest for the given run."""
    return build_manifest(req.policy, shocks=req.shocks, seed=req.seed)
