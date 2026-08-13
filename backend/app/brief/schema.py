"""Schema for the Minister's Brief export (SPEC §27 Core UI / §28.11 Evidence
Drawer / §37 North-Star).

The brief is a **rendering** layer, not a model. It takes the North-Star answer
(SPEC §37) — which already composes every deterministic layer verbatim — and
lays it out as a single, self-contained Markdown document a minister could read
or print: the one-page memo behind the dashboard. It computes **no new number**;
every figure is the same object the standalone endpoints return, so the brief
can never disagree with the tabs behind it (SPEC §34). Provenance tags travel
with the text (Observed/Estimated/Simulated/Generated), generated media stays
labelled SIMULATED, and a reproducibility footer closes the document (SPEC §32).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..northstar.schema import NorthStarAnswer, NorthStarRequest


class BriefRequest(NorthStarRequest):
    """Input to ``POST /brief`` — same contract as ``/north-star`` plus layout knobs.

    A brief is just a formatted North-Star answer, so it accepts exactly the
    North-Star request (text-or-policy, horizon, objective/constraints, shocks,
    seed) and adds two presentation-only switches.
    """

    include_answer: bool = Field(
        default=True,
        description="Embed the full structured NorthStarAnswer alongside the Markdown.",
    )
    include_media: bool = Field(
        default=True,
        description="Include the SIMULATED media-narratives section in the memo.",
    )


class TagLegendEntry(BaseModel):
    """One row of the provenance key printed in the brief header (SPEC §34)."""

    tag: str
    meaning: str


class BriefResponse(BaseModel):
    """A rendered Minister's Brief: the Markdown memo + its structured backing."""

    note: str = Field(
        default=(
            "Minister's Brief (SPEC §27/§28.11/§37): a Markdown rendering of the "
            "North-Star answer. No number is computed here — every figure is read "
            "from /north-star, which itself reuses the standalone layers verbatim, "
            "so the brief can never disagree with the endpoints (SPEC §34)."
        )
    )
    policy_id: str
    title: str
    question: str
    horizon_months: float
    horizon_label: str
    generated_from: str = Field(
        default="/north-star",
        description="The endpoint whose output this document renders.",
    )
    tag_legend: list[TagLegendEntry] = Field(
        default_factory=list, description="Provenance key printed at the top of the memo."
    )
    word_count: int = Field(description="Length of the rendered Markdown, in words.")
    markdown: str = Field(description="The self-contained Markdown memo.")
    answer: NorthStarAnswer | None = Field(
        default=None,
        description="Full structured North-Star answer (present when include_answer=True).",
    )
