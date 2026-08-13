"""System Dynamics / recursive-feedback endpoint (SPEC §7.6 + §19).

``POST /dynamics`` takes a compiled Policy DSL and integrates the recursive
feedback loop SPEC §19 calls "central to the concept": charge → mode shift →
revenue → transit capacity, and negative public support → endogenous amendment →
weaker charge → reduced revenue → slower capacity → renewed crowding.

Structural magnitudes are read from the deterministic agent-based model at the
in-force charge; the temporal coefficients coupling them over time are documented
assumptions. Deterministic and LLM-free → Simulated (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..dynamics import SystemDynamicsResult, build_system_dynamics
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/dynamics", tags=["dynamics"])


class DynamicsRequest(BaseModel):
    """Input to ``POST /dynamics``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    political_response: bool = Field(
        default=True,
        description=(
            "Enable the endogenous political-response arm of the loop (SPEC §19): "
            "sustained negative support forces an amendment that cuts the charge. "
            "The response always also reports the toggle-counterpart as a contrast."
        ),
    )


@router.post("", response_model=SystemDynamicsResult, summary="Recursive feedback loop")
def dynamics(req: DynamicsRequest) -> SystemDynamicsResult:
    """Run the deterministic stock-flow feedback simulation for ``req.policy``."""
    return build_system_dynamics(req.policy, political_response=req.political_response)
