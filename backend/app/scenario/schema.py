"""Schemas for the scenario orchestrator (SPEC §28/§29 — the killer demo).

``POST /run`` composes the whole engine into one call so the frontend (and a
judge poking the API) gets the entire §29 narrative — compile → simulate →
public reaction → parliament → amendment → re-simulate → media — in a single,
mutually-consistent payload. Every numeric section is a *reuse* of an existing
deterministic layer (no new numeric model), so the guardrails hold exactly as
they do per-endpoint: numbers are Simulated, debate/media prose is Generated,
and no LLM touches a figure (SPEC §34).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from ..baseline.schema import MetricTag
from ..media import MediaResponse
from ..opinion import PublicOpinion
from ..parliament import DebateResponse
from ..policy.dsl import CompileResponse, PolicyDSL
from ..routers.simulate import SimulateResponse
from ..simulation.amendment import Amendment, AmendmentComparison
from ..simulation.shocks import Shocks


class RunRequest(BaseModel):
    """Input to ``POST /run`` — supply *either* natural-language ``text`` or a
    pre-compiled ``policy`` DSL (at least one is required)."""

    text: Optional[str] = Field(
        default=None,
        description="Natural-language policy. Compiled to a DSL when no `policy` is given.",
    )
    policy: Optional[PolicyDSL] = Field(
        default=None,
        description="Pre-compiled Policy DSL (skips the compile step).",
    )
    jurisdiction: Optional[str] = Field(
        default=None, description="Optional jurisdiction hint for the compiler."
    )
    shocks: Optional[Shocks] = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    amendment: Optional[Amendment] = Field(
        default=None,
        description="Override the auto-proposed amendment with an explicit one.",
    )
    horizon_months: float = Field(
        default=24.0,
        ge=0.0,
        description="Horizon the headline dashboard reports (nearest checkpoint). "
        "Defaults to Year 2, the §29 demo horizon.",
    )
    seed: Optional[int] = Field(
        default=None, description="Echoed; the numeric core is deterministic."
    )

    @model_validator(mode="after")
    def _require_policy_or_text(self) -> "RunRequest":
        if self.policy is None and not (self.text and self.text.strip()):
            raise ValueError("Provide either `text` (to compile) or a pre-compiled `policy`.")
        return self


class NarrativeBeat(BaseModel):
    """One beat of the §29 killer-demo storyline, pointing at a response section."""

    timecode: str = Field(description="Approximate demo timecode, e.g. '0–10s'.")
    stage: str = Field(description="What happens, e.g. 'Compile policy'.")
    section: str = Field(description="Which response field carries the evidence.")
    description: str = Field(description="One-line narration grounded in this run.")


class HeadlineMetric(BaseModel):
    """A single dashboard tile: the policy effect on one metric at the horizon."""

    key: str
    label: str
    unit: str
    world_a: float = Field(description="Baseline value at the horizon.")
    world_b: float = Field(description="Policy value at the horizon.")
    delta: float = Field(description="World B − World A (the policy effect).")
    delta_pct: Optional[float] = Field(default=None, description="Δ as % of World A.")
    direction: str = Field(description="'down' / 'up' / 'flat' vs baseline.")
    band: list[float] = Field(
        default_factory=list, description="[low, high] Δ uncertainty band at the horizon."
    )
    tag: MetricTag = Field(MetricTag.simulated)


class ProposedAmendment(BaseModel):
    """The parliament's amendment (auto-derived or caller-supplied) + its effect."""

    proposed: bool = Field(description="Whether an amendment was applied.")
    source: str = Field(
        description="'caller', 'auto:equity', 'auto:reinvestment', or 'none'."
    )
    rationale: str = Field(description="Why this amendment (evidence-grounded).")
    amendment: Optional[Amendment] = None
    comparison: Optional[AmendmentComparison] = Field(
        default=None, description="Δ(amended − original) across checkpoints (SPEC §12/§21)."
    )


class RunResponse(BaseModel):
    """The full §29 demo narrative in one mutually-consistent payload."""

    provenance: str = Field(
        default=(
            "Composed scenario. Every number is Simulated (one deterministic "
            "agent-based run shared across all sections); debate and media prose "
            "is Generated; no LLM touches any figure (SPEC §34)."
        )
    )
    note: str = Field(
        default=(
            "One call runs the killer-demo pipeline end-to-end so every section "
            "reads the same compiled policy and the same simulation — the "
            "dashboard, parliament, amendment and media can never disagree."
        )
    )
    policy_id: str
    horizon_months: float
    horizon_label: str
    compiled: Optional[CompileResponse] = Field(
        default=None, description="Compiler output when `text` was supplied (SPEC §3)."
    )
    narrative: list[NarrativeBeat] = Field(default_factory=list)
    headline: list[HeadlineMetric] = Field(
        default_factory=list, description="Dashboard tiles at the chosen horizon."
    )
    net_support: float = Field(
        description="Overall net public support (support − oppose), from /public."
    )
    simulation: SimulateResponse
    public: PublicOpinion
    parliament: DebateResponse
    amendment: ProposedAmendment
    media: MediaResponse
