"""Distributional microsimulation endpoint (SPEC §7.3).

``POST /microsim`` takes a compiled Policy DSL and returns the policy's person-
level distributional impact: who gains, who loses, by how much, and broken down
by income decile, household type, home neighbourhood and occupation — plus a
charge-burden regressivity gradient.

Impacts come from each synthetic commuter's change in minimum generalized cost
(World B − World A) under the same deterministic mode-choice model as
``/simulate``. Every number is Simulated (money-equivalents use a documented
Estimated value-of-time); no LLM touches the numeric path (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..microsim.model import build_microsim_report
from ..microsim.schema import MicrosimReport
from ..policy.dsl import PolicyDSL

router = APIRouter(prefix="/microsim", tags=["microsim"])


class MicrosimRequest(BaseModel):
    """Input to ``POST /microsim``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")


@router.post("", response_model=MicrosimReport,
             summary="Person-level distributional impact of a policy (SPEC §7.3)")
def microsim(req: MicrosimRequest) -> MicrosimReport:
    """Return the distributional microsimulation report (SPEC §7.3)."""
    return build_microsim_report(req.policy)
