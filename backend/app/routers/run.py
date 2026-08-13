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
"""

from __future__ import annotations

from fastapi import APIRouter

from ..scenario import RunRequest, RunResponse, run_scenario

router = APIRouter(tags=["scenario"])


@router.post("/run", response_model=RunResponse, summary="Run the full demo pipeline")
def run(req: RunRequest) -> RunResponse:
    """Compose compile → simulate → public → parliament → amendment → media."""
    return run_scenario(req)
