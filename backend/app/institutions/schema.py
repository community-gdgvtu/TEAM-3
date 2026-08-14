"""Schemas for the institutional review layer (SPEC §18)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag
from ..parliament.schema import EvidenceCitation


class Verdict(str, Enum):
    """An institutional agent's professional verdict on the policy."""

    clear = "clear"  # proceed on this dimension
    conditional = "conditional"  # proceed only with the stated conditions
    concern = "concern"  # material issues to resolve
    block = "block"  # should not proceed as drafted on this dimension


# Severity ordering for computing the overall (worst) verdict.
_ORDER = {Verdict.clear: 0, Verdict.conditional: 1, Verdict.concern: 2, Verdict.block: 3}


def worst(verdicts: list[Verdict]) -> Verdict:
    """Return the most severe verdict in the list (defaults to clear)."""
    return max(verdicts, key=lambda v: _ORDER[v], default=Verdict.clear)


class Finding(BaseModel):
    """One specific, evidence-anchored observation within a review."""

    dimension: str = Field(description="What aspect this finding is about.")
    detail: str
    severity: str = Field(description="'info' | 'watch' | 'risk' | 'blocker'.")


class InstitutionalReview(BaseModel):
    """One institutional agent's structured assessment (SPEC §18)."""

    agent: str = Field(description="Agent name, e.g. 'Climate Agent'.")
    mandate: str = Field(description="What this agent is responsible for assessing.")
    spec_ref: str = Field(default="§18")
    verdict: Verdict
    summary: str = Field(description="One-line professional judgement.")
    findings: list[Finding] = Field(default_factory=list)
    recommendation: str = Field(description="Concrete next step / condition.")
    citations: list[EvidenceCitation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class InstitutionsResponse(BaseModel):
    """The full institutional review panel for a policy run (SPEC §18)."""

    provenance: MetricTag = Field(
        MetricTag.generated,
        description="Review prose is Generated; every cited number is Simulated.",
    )
    note: str = Field(
        default=(
            "Institutional review panel: each agent assesses the policy against a "
            "professional mandate using the deterministic simulation's Δ metrics, "
            "event ledger and provenance. Verdicts and cited numbers come from the "
            "model — no LLM produces a figure (SPEC §18/§34)."
        )
    )
    policy_id: str
    reviews: list[InstitutionalReview] = Field(default_factory=list)
    overall_verdict: Verdict = Field(description="The most severe single verdict.")
    verdict_tally: dict = Field(default_factory=dict)
    summary: str = Field(default="", description="Deterministic synthesis across agents.")
