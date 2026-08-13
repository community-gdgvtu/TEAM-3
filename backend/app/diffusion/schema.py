"""Schemas for the opinion-diffusion engine (SPEC §14).

Opinions live on a bipolar scale in ``[-1, +1]`` (−1 = strong oppose, +1 = strong
support). The graph is abstract (SPEC §14): typed nodes with weighted directed
influence edges. Everything here is a deterministic transform of the cohort
opinion model + documented actor priors → tagged Simulated (SPEC §34).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class DiffusionNode(BaseModel):
    """One actor in the social graph."""

    id: str = Field(description="Stable node id, e.g. 'citizen_low'.")
    type: str = Field(
        description="cohort | journalist | politician | institution | influencer | "
        "community_group | business."
    )
    label: str
    size: int = Field(0, description="Represented population (0 for institutional actors).")
    susceptibility: float = Field(
        ge=0.0, le=1.0, description="Friedkin–Johnsen λ: openness to persuasion."
    )
    initial_opinion: float = Field(description="Opinion at round 0, in [-1,1].")
    final_opinion: float = Field(description="Opinion at the last round, in [-1,1].")
    opinion_prior_source: str = Field(
        description="Where the round-0 opinion came from (model / documented prior)."
    )


class DiffusionEdge(BaseModel):
    """A directed influence edge ``source → target`` (target listens to source)."""

    source: str
    target: str
    weight: float = Field(description="Normalised influence weight (target's row sums to 1).")
    kind: str = Field(
        description="social_influence | media_exposure | geography | workplace | "
        "political_affinity | institutional."
    )


class OpinionTrajectory(BaseModel):
    """One node's opinion over the information rounds."""

    node_id: str
    opinions: list[float] = Field(description="Opinion per round (index 0 = round 0).")


class Coalition(BaseModel):
    """A bloc that has converged to a shared stance by the final round."""

    stance: str = Field(description="'support' | 'oppose' | 'contested'.")
    members: list[str] = Field(default_factory=list, description="Node ids in the bloc.")
    citizen_share: float = Field(
        description="Share of the citizen population represented by this bloc (0–1)."
    )
    mean_opinion: float = Field(description="Size-weighted mean opinion of the bloc.")


class InfoShock(BaseModel):
    """An exogenous information shock injected at one round (SPEC §14)."""

    round: int = Field(ge=0, description="Round at which the shock lands.")
    node: str = Field(description="Node id the shock hits.")
    delta: float = Field(description="Additive opinion shift, clamped into [-1,1].")
    label: str = Field(default="", description="Human description, e.g. 'scandal'.")


class DiffusionResult(BaseModel):
    """Full opinion-diffusion run for a policy (SPEC §14)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Deterministic Friedkin–Johnsen opinion diffusion over an abstract "
            "social graph. Citizen round-0 opinions come from the cohort opinion "
            "model; actor priors are documented constants. Rounds are "
            "information-diffusion steps, NOT the physical Time-Machine horizon. "
            "No LLM produced any number (SPEC §14/§34)."
        )
    )
    policy_id: str
    rounds: int = Field(description="Number of diffusion rounds simulated.")
    nodes: list[DiffusionNode] = Field(default_factory=list)
    edges: list[DiffusionEdge] = Field(default_factory=list)
    trajectories: list[OpinionTrajectory] = Field(default_factory=list)
    salience: list[float] = Field(
        default_factory=list, description="Issue salience per round (engagement, 0–1)."
    )
    polarisation: list[float] = Field(
        default_factory=list, description="Opinion polarisation per round (0–1)."
    )
    coalitions: list[Coalition] = Field(default_factory=list)
    initial_net_support: float = Field(description="Citizen-weighted mean opinion, round 0.")
    final_net_support: float = Field(description="Citizen-weighted mean opinion, final round.")
    dominant_narrative: str = Field(description="Which framing prevails among citizens.")
    shocks_applied: list[InfoShock] = Field(default_factory=list)
    assumptions: dict = Field(
        default_factory=dict, description="Graph + dynamics parameters used (auditable)."
    )
