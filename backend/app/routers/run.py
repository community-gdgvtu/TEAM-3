"""Scenario orchestrator endpoint (SPEC §28/§29 — the killer demo).

``POST /run`` composes the whole engine into one call: it compiles the policy
(or accepts a compiled DSL), runs the deterministic World-A/B/Δ simulation, the
cohort public reaction, the model parliament, an (auto-derived or supplied)
amendment re-simulation, and the simulated media feed — returning the entire
§29 narrative in a single, mutually-consistent payload. It introduces **no new
numeric model**: every section reuses an existing layer and reads the same
compiled policy and the same simulation, so the dashboard, parliament and media
can never disagree. Numbers are Simulated; debate/media prose is Generated; no
LLM touches a figure (SPEC §34).

``GET /run/example`` runs that same pipeline on the canonical §28 demo
congestion charge with **no request body**, so a judge or the UI can pull the
whole §29 narrative in one keyless call (mirrors ``GET /brief/example`` and
``GET /backtest/example``).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..scenario import RunRequest, RunResponse, run_scenario

router = APIRouter(tags=["scenario"])

#: The canonical §28 demo policy, orchestrated by ``GET /run/example``.
_DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


@router.post("/run", response_model=RunResponse, summary="Run the full demo pipeline")
def run(req: RunRequest) -> RunResponse:
    """Compose compile → simulate → public → parliament → amendment → media."""
    return run_scenario(req)


@router.get(
    "/run/example",
    response_model=RunResponse,
    summary="Full §29 demo pipeline for the canonical congestion charge (no body)",
)
def run_example() -> RunResponse:
    """Orchestrate the §28 demo policy end-to-end (no request body needed)."""
    return run_scenario(RunRequest(text=_DEMO_TEXT))
