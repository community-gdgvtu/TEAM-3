"""Model Parliament endpoint (ROADMAP M5, SPEC §11/§12).

``POST /parliament/debate`` takes a compiled Policy DSL (plus optional shocks),
runs the deterministic simulation, and returns an adversarial debate: five
personas each argue an evidence-grounded position citing the Δ(B−A) metrics and
the event ledger. Speech prose is LLM-produced when a key is configured and a
deterministic template otherwise; either way every cited number is Simulated and
nothing is invented (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..parliament import (
    AskRequest,
    AskResponse,
    DebateRequest,
    DebateResponse,
    FailureModeRegister,
    ask_persona,
    build_failure_register,
    run_debate,
    simulate_brief,
)

router = APIRouter(prefix="/parliament", tags=["parliament"])


@router.post("/debate", response_model=DebateResponse, summary="Adversarial policy debate")
def debate(req: DebateRequest) -> DebateResponse:
    """Stress-test ``req.policy`` in the Model Parliament and return the debate."""
    return run_debate(req.policy, shocks=req.shocks, seed=req.seed)


@router.post(
    "/failure-modes",
    response_model=FailureModeRegister,
    summary="Devil's Advocate → ranked Failure Mode Register",
)
def failure_modes(req: DebateRequest) -> FailureModeRegister:
    """Return the ranked Failure Mode Register for ``req.policy`` (SPEC §12).

    Each mode carries risk/mechanism/severity/probability/evidence/mitigation and
    is ranked by expected risk. Risk scores are Estimated; cited evidence is
    Simulated (SPEC §34).
    """
    brief = simulate_brief(req.policy, shocks=req.shocks)
    return build_failure_register(brief)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask one persona a follow-up question",
)
def ask(req: AskRequest) -> AskResponse:
    """Answer ``req.question`` in ``req.persona``'s voice (SPEC §11/§34).

    Grounded in the same deterministic simulation as ``/parliament/debate`` —
    the persona's evidence points are unchanged, only the prose responds
    directly to the question. LLM-phrased when a key is configured, a
    keyword-matched template otherwise; either way nothing is invented.
    """
    try:
        return ask_persona(req.policy, req.persona, req.question, shocks=req.shocks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
