"""Model Parliament endpoint (ROADMAP M5, SPEC §11/§12).

``POST /parliament/debate`` takes a compiled Policy DSL (plus optional shocks),
runs the deterministic simulation, and returns an adversarial debate: five
personas each argue an evidence-grounded position citing the Δ(B−A) metrics and
the event ledger. Speech prose is LLM-produced when a key is configured and a
deterministic template otherwise; either way every cited number is Simulated and
nothing is invented (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..parliament import DebateRequest, DebateResponse, run_debate

router = APIRouter(prefix="/parliament", tags=["parliament"])


@router.post("/debate", response_model=DebateResponse, summary="Adversarial policy debate")
def debate(req: DebateRequest) -> DebateResponse:
    """Stress-test ``req.policy`` in the Model Parliament and return the debate."""
    return run_debate(req.policy, shocks=req.shocks, seed=req.seed)
