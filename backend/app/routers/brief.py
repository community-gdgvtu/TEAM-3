"""Minister's Brief endpoint (SPEC §27 Core UI / §28.11 Evidence Drawer / §37).

``POST /brief`` renders the North-Star answer as a single self-contained
Markdown memo — the one-page brief behind the dashboard that a minister could
read or print. ``GET /brief/example`` renders the canonical demo congestion
charge so a judge can see the artifact with no request body.

It introduces **no new numeric model**: the brief delegates the whole answer to
``/north-star`` (which itself reuses every standalone layer verbatim) and only
formats it, so the memo can never disagree with the tabs behind it. Every figure
carries its provenance tag; media stays labelled SIMULATED; the document ends
with a reproducibility footer (SPEC §32/§34).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..brief import BriefRequest, BriefResponse, build_brief

router = APIRouter(tags=["brief"])

#: The canonical §28 demo policy, rendered by ``GET /brief/example``.
_DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


@router.post(
    "/brief",
    response_model=BriefResponse,
    summary="Minister's Brief: the North-Star answer as a Markdown memo (SPEC §27/§37)",
)
def brief(req: BriefRequest) -> BriefResponse:
    """Render the Minister's Brief for a single policy."""
    return build_brief(req)


@router.get(
    "/brief/example",
    response_model=BriefResponse,
    summary="Minister's Brief for the canonical demo congestion charge",
)
def brief_example() -> BriefResponse:
    """Render the brief for the §28 demo policy (no request body needed)."""
    return build_brief(
        BriefRequest(
            text=_DEMO_TEXT,
            objective={"reduce_transport_emissions_pct": 20},
            constraints={"max_low_income_burden_increase_pct": 2},
        )
    )
