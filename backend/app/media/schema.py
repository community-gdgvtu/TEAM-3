"""Schemas for the simulated media generator (SPEC §15).

Media coverage is generated from **archetypes** (public-service broadcaster,
business press, local paper, tabloid, environmental, industry) rather than real
outlets. Every artifact is explicitly labelled SIMULATED, carries no real
byline, and cites only the event-ledger entries / outcome metrics / opinion state
it was built from — narratives may not invent quantitative events (SPEC §15/§34).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag

#: The mandatory disclaimer every artifact must carry (SPEC §15).
SIMULATED_LABEL = "SIMULATED — NOT A REAL ARTICLE OR FORECAST OF A SPECIFIC OUTLET"


class MediaArchetype(str, Enum):
    """Outlet archetypes (SPEC §15) — deliberately generic, never a real outlet."""

    public_broadcaster = "public_broadcaster"
    business_press = "business_press"
    local_news = "local_news"
    tabloid = "tabloid"
    environmental = "environmental"
    industry = "industry"


class Headline(BaseModel):
    """One simulated media artifact (SPEC §15)."""

    archetype: MediaArchetype
    outlet_label: str = Field(description="Fictional generic outlet name (never real).")
    headline: str
    standfirst: str = Field(description="Sub-headline / one-line context.")
    angle: str = Field(description="The lens this archetype applies.")
    sentiment: str = Field(description="'positive' | 'critical' | 'mixed'.")
    cited_refs: list[str] = Field(
        default_factory=list, description="Event ids / metric keys the story is built on."
    )
    label: str = Field(default=SIMULATED_LABEL, description="Mandatory SIMULATED banner.")
    provenance: MetricTag = Field(MetricTag.generated)


class MediaScenario(BaseModel):
    """A batch of archetype headlines at one horizon (e.g. Month 5, Year 2)."""

    label: str = Field(description="Horizon label, e.g. 'Month 5'.")
    scenario_month: float
    headlines: list[Headline] = Field(default_factory=list)


class MediaResponse(BaseModel):
    """Full simulated media coverage for a policy (SPEC §15)."""

    provenance: MetricTag = Field(
        MetricTag.generated,
        description="Media prose is Generated; every cited figure is Simulated.",
    )
    disclaimer: str = Field(default=SIMULATED_LABEL)
    note: str = Field(
        default=(
            "Simulated media generated strictly from the event ledger, outcome "
            "metrics and opinion state. Archetypes, not real outlets; no real "
            "bylines; no invented quantitative events (SPEC §15/§34)."
        )
    )
    policy_id: str
    method: str = Field(default="template", description="'llm' or 'template'.")
    scenarios: list[MediaScenario] = Field(default_factory=list)
