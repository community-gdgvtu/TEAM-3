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

``GET /north-star/example`` composes that same §37 answer for the canonical §28
demo congestion charge with **no request body** — the same inputs the Minister's
Brief renders — so a judge or the UI can pull the whole answer in one keyless
call (mirrors ``GET /brief/example`` / ``GET /run/example``).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..northstar import NorthStarAnswer, NorthStarRequest, run_north_star

router = APIRouter(tags=["northstar"])

#: The canonical §28 demo policy, composed by ``GET /north-star/example``
#: (identical inputs to ``GET /brief/example``, which delegates to this layer).
_DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


@router.post(
    "/north-star",
    response_model=NorthStarAnswer,
    summary="The North-Star answer: 'What happens if we implement this?' (SPEC §37)",
)
def north_star(req: NorthStarRequest) -> NorthStarAnswer:
    """Compose the full §37 minister's answer for a single policy."""
    return run_north_star(req)


@router.get(
    "/north-star/example",
    response_model=NorthStarAnswer,
    summary="The §37 North-Star answer for the canonical demo congestion charge (no body)",
)
def north_star_example() -> NorthStarAnswer:
    """Compose the §37 answer for the §28 demo policy (no request body needed)."""
    return run_north_star(
        NorthStarRequest(
            text=_DEMO_TEXT,
            objective={"reduce_transport_emissions_pct": 20},
            constraints={"max_low_income_burden_increase_pct": 2},
        )
    )
