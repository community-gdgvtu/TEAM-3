"""Press conference endpoint (SPEC §16).

``POST /press-conference`` takes a compiled Policy DSL (plus optional shocks and
a horizon) and stages a simulated press conference: a spokesperson opening
statement and five archetype journalist exchanges, each grounded in a specific Δ
metric, event-ledger entry or opinion figure copied from the deterministic
simulation. An LLM may polish the prose; it never produces a number (SPEC §16/§34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..press.conference import run_press_conference
from ..press.schema import PressConference
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/press-conference", tags=["press-conference"])


class PressConferenceRequest(BaseModel):
    """Input to ``POST /press-conference``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    horizon_months: float = Field(
        default=5.0,
        ge=0.0,
        description="When the conference is held; snapped to the nearest checkpoint "
        "at or before this month (default 5 months).",
    )
    use_llm: bool = Field(
        default=True,
        description="Allow LLM prose polish (prose only). Falls back to templates "
        "when no key is configured. Numbers are never LLM-produced (SPEC §34).",
    )


@router.post("", response_model=PressConference, summary="Simulate a press conference (SPEC §16)")
def press_conference(req: PressConferenceRequest) -> PressConference:
    """Return the simulated press conference for the supplied policy."""
    return run_press_conference(
        req.policy,
        shocks=req.shocks,
        horizon_months=req.horizon_months,
        use_llm=req.use_llm,
    )
