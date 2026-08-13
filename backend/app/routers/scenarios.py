"""Scenario-presets endpoints (SPEC §3 / §27 / §28).

``GET /scenarios`` returns the discoverable menu of canonical demo policies;
``GET /scenarios/{scenario_id}`` returns one card. Every card carries its
natural-language prompt, the live compiler output (DSL + reviewable assumptions),
and two ready-to-POST bodies — one for ``/simulate`` (and any endpoint taking a
compiled ``policy``) and one for the composed-answer endpoints (``/run``,
``/north-star``, ``/brief``). Deterministic, no numeric model, no LLM (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..scenarios import ScenarioCard, ScenarioLibrary, build_library, get_scenario, scenario_ids

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=ScenarioLibrary, summary="Menu of canonical demo policies (SPEC §3/§28)")
def scenarios() -> ScenarioLibrary:
    """Return the full curated library of ready-to-run policy scenarios."""
    return build_library()


@router.get(
    "/{scenario_id}",
    response_model=ScenarioCard,
    summary="One canonical scenario by id",
    responses={404: {"description": "Unknown scenario id (valid ids returned)."}},
)
def scenario(scenario_id: str) -> ScenarioCard | JSONResponse:
    """Return a single scenario card, or 404 echoing the valid ids."""
    card = get_scenario(scenario_id)
    if card is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Unknown scenario id: {scenario_id!r}",
                "valid_ids": scenario_ids(),
            },
        )
    return card
