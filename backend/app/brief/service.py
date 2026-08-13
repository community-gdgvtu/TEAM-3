"""Minister's Brief service (SPEC §27/§28.11/§37).

Composes the brief by delegating the *entire* numeric answer to
:func:`run_north_star` and then rendering it. This module owns no model and no
number — it is a formatter over the North-Star answer, so the memo is guaranteed
consistent with `/north-star` and, transitively, with every standalone endpoint
(SPEC §34).
"""

from __future__ import annotations

from ..northstar import run_north_star
from .render import TAG_LEGEND, render_brief_markdown
from .schema import BriefRequest, BriefResponse, TagLegendEntry


def build_brief(req: BriefRequest) -> BriefResponse:
    """Build the Minister's Brief for one policy."""
    answer = run_north_star(req)

    markdown = render_brief_markdown(
        answer,
        include_media=req.include_media,
        seed=req.seed,
    )

    return BriefResponse(
        policy_id=answer.policy_id,
        title=f"Minister's Brief — policy {answer.policy_id}",
        question=answer.question,
        horizon_months=answer.horizon_months,
        horizon_label=answer.horizon_label,
        tag_legend=[TagLegendEntry(tag=t, meaning=m) for t, m in TAG_LEGEND],
        word_count=len(markdown.split()),
        markdown=markdown,
        answer=answer if req.include_answer else None,
    )
