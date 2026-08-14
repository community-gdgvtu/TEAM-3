"""Response schema for the stress-testing layer (SPEC §20)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class MetricStress(BaseModel):
    """How one headline metric's policy benefit holds up under one shock.

    ``delta_*`` is the policy effect Δ(World B − World A). Because a shock is
    applied to *both* worlds, the delta still isolates the policy — so comparing
    the delta under the shock to the delta under the transparent baseline tells us
    whether the policy still delivers (SPEC §20/§21).
    """

    key: str
    label: str
    unit: str
    intended_direction: str = Field(
        description="'decrease' or 'increase' — the direction of a *good* policy "
        "effect for this metric (e.g. cordon traffic should decrease)."
    )
    delta_baseline: float = Field(
        description="Policy Δ(B−A) under the transparent no-shock baseline context."
    )
    delta_baseline_pct: float | None = None
    delta_shocked: float = Field(
        description="Policy Δ(B−A) under this shock's context."
    )
    delta_shocked_pct: float | None = None
    retained_pct: float | None = Field(
        default=None,
        description="Fraction of the baseline benefit retained under the shock, as "
        "a percent (100 = unchanged, <0 = the effect reversed). None when the "
        "policy had no benefit on this metric even at baseline.",
    )
    verdict: str = Field(
        description="robust | strengthened | weakened | neutralised | reversed | n/a"
    )
    note: str


class ScenarioResult(BaseModel):
    """The policy re-run under one named scenario (or the no-shock baseline)."""

    key: str
    label: str
    category: str
    fidelity: str = Field(
        description="modelled | partial | proxy — how faithfully this MVP model "
        "represents the shock (SPEC §34 honesty)."
    )
    confidence: str = Field(description="high | medium | low, from fidelity × horizon.")
    caveat: str = ""
    overrides: dict = Field(
        default_factory=dict, description="The exact Shocks knobs applied (auditable)."
    )
    metrics: list[MetricStress] = Field(default_factory=list)
    verdict: str = Field(description="holds | degrades | fails | reference")
    summary: str


class StressRobustness(BaseModel):
    """Roll-up: which shocks the policy withstands and which break it (SPEC §20)."""

    robust_to: list[str] = Field(default_factory=list)
    degrades_under: list[str] = Field(default_factory=list)
    fails_under: list[str] = Field(default_factory=list)
    headline: str


class StressReport(BaseModel):
    """Full stress-test payload for ``POST /stress-test`` (SPEC §20)."""

    provenance: MetricTag = Field(
        MetricTag.simulated,
        description="Policy deltas are Simulated; shock magnitudes are Estimated "
        "scenario assumptions. No LLM in the numeric path (SPEC §34).",
    )
    policy_id: str
    note: str = Field(
        default=(
            "Each named shock is a transparent scenario assumption applied to BOTH "
            "worlds, so Δ(B−A) still isolates the policy. A scenario 'fails' when "
            "the policy's benefit on a headline metric is neutralised or reversed "
            "relative to the no-shock baseline (SPEC §20)."
        )
    )
    horizon_months: float
    horizon_label: str
    baseline: ScenarioResult = Field(
        description="The policy under the transparent no-shock baseline (reference)."
    )
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    robustness: StressRobustness
