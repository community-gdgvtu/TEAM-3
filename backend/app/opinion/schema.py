"""Schemas for the cohort public-opinion model (SPEC §13).

The public is never one agent: opinion is reported as a **distribution** across
the six SPEC §13 buckets (Strong support … Strong oppose, plus Uncertain), broken
out by cohort (income band × geography × travel mode) and aggregated overall.

Guardrail (SPEC §34): the model is deterministic and driven by the agent-based
material impact → tagged Simulated, not an invented poll.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class OpinionDistribution(BaseModel):
    """Support distribution over the six SPEC §13 buckets (fractions sum to ~1)."""

    strong_support: float = 0.0
    support: float = 0.0
    neutral: float = 0.0
    oppose: float = 0.0
    strong_oppose: float = 0.0
    uncertain: float = 0.0
    #: Net support = (strong_support + support) − (oppose + strong_oppose), in [-1,1].
    net_support: float = 0.0


class CohortOpinion(BaseModel):
    """One population cohort's opinion (SPEC §13)."""

    key: str = Field(description="Cohort id, e.g. 'low|inbound|car'.")
    income_band: str
    geography: str = Field(description="'inbound' (commutes into CBD) or 'local'.")
    travel_mode: str = Field(description="Baseline travel mode of the cohort.")
    size: int = Field(description="Number of micro-agents in the cohort.")
    mean_material_impact: float = Field(
        description="Mean change in own travel cost (minutes-equiv; + = worse off)."
    )
    mean_fairness: float = Field(description="Mean perceived-fairness signal [-1,1].")
    mean_support: float = Field(description="Mean latent support score [-1,1].")
    distribution: OpinionDistribution


class PublicOpinion(BaseModel):
    """Full public-reaction result for a policy (SPEC §13)."""

    provenance: MetricTag = Field(
        MetricTag.simulated,
        description="Deterministic structural opinion model → Simulated.",
    )
    note: str = Field(
        default=(
            "Cohort opinion from a deterministic model: each micro-agent's own "
            "modelled material impact + perceived fairness + ideological prior → a "
            "support distribution. Not a poll; no LLM produced any number (SPEC §34)."
        )
    )
    policy_id: str
    population: int
    overall: OpinionDistribution
    cohorts: list[CohortOpinion] = Field(default_factory=list)
    params: dict = Field(default_factory=dict, description="Opinion assumptions used.")
