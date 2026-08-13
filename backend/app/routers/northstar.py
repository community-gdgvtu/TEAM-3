"""North-Star answer endpoint (SPEC §37 — the North-Star Experience).

``POST /north-star`` answers a minister's "What happens if we implement this?"
with the exact fixed narrative SPEC §37 specifies — baseline, historical
analogues, mechanisms, median outcome, uncertainty, winners, losers, failure
modes, the opposition's strongest argument, opinion evolution, media narratives,
three risk-reducing amendments, each amendment's effect, the best-fit policy
configuration, and every assumption + piece of evidence behind the conclusions.

It introduces **no new numeric model**: every section reuses an existing layer
(``/simulate``, ``/analogues``, ``/uncertainty``, ``/microsim``,
``/parliament/failure-modes``, ``/parliament/debate``, ``/diffusion``,
``/media``, the amendment comparison, ``/optimise``, ``/registry``) reading the
same compiled policy and the same simulation, so the answer can never disagree
with the standalone endpoints. Numbers are Simulated/Estimated; debate & media
prose is Generated; transparency artifacts are Observed; no LLM touches a figure
(SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..northstar import NorthStarAnswer, NorthStarRequest, run_north_star

router = APIRouter(tags=["northstar"])


@router.post(
    "/north-star",
    response_model=NorthStarAnswer,
    summary="The North-Star answer: 'What happens if we implement this?' (SPEC §37)",
)
def north_star(req: NorthStarRequest) -> NorthStarAnswer:
    """Compose the full §37 minister's answer for a single policy."""
    return run_north_star(req)
