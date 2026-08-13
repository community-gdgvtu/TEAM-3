"""Pydantic schemas for the uncertainty engine (ROADMAP M7, SPEC §24).

Turns a single deterministic policy run into a *fan of plausible futures*: a
Monte-Carlo sweep over the key uncertain assumptions (elasticities, service
response, emissions factor) yields a median trajectory with 50/80/95% intervals,
a one-at-a-time sensitivity ranking of the most influential assumptions, and a
behavioural-regime ensemble measuring model disagreement (SPEC §24).

Every number is produced by re-running the deterministic structural model with
perturbed *input assumptions*; the LLM never touches the numeric path (SPEC §34).
The perturbed results are Simulated.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class Interval(BaseModel):
    """A central estimate's [low, high] band at one confidence level."""

    level: int = Field(description="Confidence level, e.g. 50, 80, 95 (percent).")
    low: float
    high: float


class HorizonBand(BaseModel):
    """The fan at one Time-Machine checkpoint: median + nested intervals."""

    t_months: float
    t_years: float
    median: float
    intervals: list[Interval] = Field(default_factory=list)


class SensitivityEntry(BaseModel):
    """One assumption's influence on the metric (one-at-a-time swing)."""

    rank: int
    name: str = Field(description="Assumption key, e.g. 'money_to_minutes'.")
    label: str = Field(description="Human-readable assumption name.")
    unit: str = Field(default="")
    low_value: float = Field(description="Low end of the assumption's plausible range.")
    high_value: float = Field(description="High end of the assumption's plausible range.")
    delta_at_low: float = Field(description="Metric Δ when the assumption is at its low.")
    delta_at_high: float = Field(description="Metric Δ when the assumption is at its high.")
    swing: float = Field(description="|Δ_high − Δ_low| — the influence magnitude.")
    swing_pct_of_median: float | None = Field(
        default=None, description="Swing as % of the |median| impact (None when ≈0)."
    )
    direction: str = Field(
        description="How the metric moves as the assumption rises: 'up' | 'down' | 'flat'."
    )


class EnsembleVariant(BaseModel):
    """One behavioural-regime run in the model-disagreement ensemble."""

    name: str
    label: str
    delta: float = Field(description="Metric Δ at the headline horizon under this regime.")
    description: str = ""


class ModelDisagreement(BaseModel):
    """Spread across alternative behavioural regimes (SPEC §24)."""

    variants: list[EnsembleVariant] = Field(default_factory=list)
    spread: float = Field(description="max(delta) − min(delta) across regimes.")
    note: str = Field(
        default="Alternative behavioural regimes (low/central/high response). A wide "
        "spread means the outcome is regime-sensitive, not settled."
    )


class UncertaintyResult(BaseModel):
    """Full uncertainty payload for one metric (SPEC §24)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Monte-Carlo sweep over uncertain input assumptions re-running the "
            "deterministic model. Median + 50/80/95% intervals form a fan of "
            "plausible futures; sensitivity and ensemble are exact re-runs. No LLM "
            "produced any number (SPEC §34)."
        )
    )
    policy_id: str
    metric_key: str
    metric_label: str
    unit: str
    horizon: Checkpoint = Field(description="Headline horizon the summary is quoted at.")

    point_estimate: float = Field(
        description="Δ at the default (central) assumptions — the deterministic headline."
    )
    median: float = Field(description="Median Δ across the Monte-Carlo samples.")
    mean: float
    intervals: list[Interval] = Field(
        default_factory=list, description="50/80/95% intervals at the headline horizon."
    )
    samples: int = Field(description="Monte-Carlo sample count.")
    seed: int = Field(description="RNG seed (runs are reproducible).")

    fan: list[HorizonBand] = Field(
        default_factory=list,
        description="Median + intervals at every checkpoint — the fan of futures.",
    )
    influential_assumptions: list[SensitivityEntry] = Field(
        default_factory=list, description="Most-influential assumptions, ranked (SPEC §24)."
    )
    model_disagreement: ModelDisagreement
    swept_assumptions: list[str] = Field(
        default_factory=list, description="Which assumptions the sweep varied (auditable)."
    )
