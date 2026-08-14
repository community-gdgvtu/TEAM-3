"""Schemas for the Model Parliament debate (ROADMAP M5, SPEC §11/§12).

The parliament is an **adversarial policy stress test**: a panel of personas
argue for and against the compiled policy, each grounding every claim in the
simulation's Δ(B−A) metrics and the event ledger (SPEC §10). The structured
:class:`Argument` keeps the *evidence* separate from the *prose* so the guardrail
holds: the numbers come from the deterministic model, and an LLM (when present)
only phrases them — it never invents a figure (SPEC §34).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks


class Stance(str, Enum):
    """A persona's overall position on the motion."""

    support = "support"
    oppose = "oppose"
    conditional = "conditional"  # support only with amendments
    challenge = "challenge"  # neutral stress-test / risk-surfacing


class EvidenceCitation(BaseModel):
    """A pointer from an argument to a specific model output (SPEC §10/§26)."""

    kind: str = Field(description="'metric' or 'event'.")
    ref: str = Field(description="Metric key (e.g. 'mode_share.car_pct') or event id.")
    detail: str = Field(description="Human-readable value/context for the citation.")
    tag: MetricTag = Field(MetricTag.simulated)


class Argument(BaseModel):
    """One persona's evidence-grounded contribution to the debate."""

    persona: str = Field(description="Speaker name, e.g. 'Government'.")
    role: str = Field(description="Their function in the chamber.")
    stance: Stance
    headline: str = Field(description="One-line position.")
    points: list[str] = Field(
        default_factory=list, description="Evidence-grounded argument points."
    )
    speech: str = Field(
        default="", description="Prose rendering of the points (LLM or template)."
    )
    citations: list[EvidenceCitation] = Field(default_factory=list)
    confidence: float = Field(
        ge=0.0, le=1.0, description="How strongly the evidence supports this stance."
    )


class DebateRequest(BaseModel):
    """Input to ``POST /parliament/debate``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL to stress-test.")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors for the simulation."
    )
    seed: int | None = Field(default=None, description="Echoed; model is deterministic.")


class AskRequest(BaseModel):
    """Input to ``POST /parliament/ask`` — a follow-up question to one persona."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL the persona argues over.")
    persona: str = Field(
        "Government",
        description=(
            "Which persona to address: 'Government', 'Opposition', "
            "'Equity Advocate', 'Economist', or \"Devil's Advocate\"."
        ),
    )
    question: str = Field(min_length=1, max_length=500, description="The question to ask.")
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors for the simulation."
    )


class AskResponse(BaseModel):
    """Output of ``POST /parliament/ask``."""

    provenance: MetricTag = Field(
        MetricTag.generated,
        description="The answer prose is Generated; every cited number is Simulated.",
    )
    persona: str
    role: str
    stance: Stance
    question: str
    answer: str = Field(description="The persona's in-character answer.")
    method: str = Field(description="'llm' or 'template' — how the prose was produced.")
    citations: list[EvidenceCitation] = Field(
        default_factory=list,
        description="The persona's underlying evidence citations (context, not necessarily all quoted).",
    )


class DebateResponse(BaseModel):
    """Output of the parliament debate."""

    provenance: MetricTag = Field(
        MetricTag.generated,
        description="The debate prose is Generated; every cited number is Simulated.",
    )
    note: str = Field(
        default=(
            "Adversarial policy stress test. Argument prose may be LLM-generated, "
            "but every quantitative claim cites a Simulated metric or a ledger "
            "event — no figure is invented (SPEC §11/§34)."
        )
    )
    policy_id: str
    motion: str = Field(description="The question before the chamber.")
    method: str = Field(description="'llm' or 'template' — how the prose was produced.")
    arguments: list[Argument] = Field(default_factory=list)
    tally: dict = Field(
        default_factory=dict, description="Count of personas by stance."
    )
    summary: str = Field(description="Deterministic synthesis of the debate.")
