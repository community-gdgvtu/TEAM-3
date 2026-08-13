"""Pydantic schemas for the ensemble forecast (SPEC §8)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class MethodEstimate(BaseModel):
    """One independent estimator's view of the flagship metric (SPEC §7 layer)."""

    method_id: str = Field(description="Stable key, e.g. 'structural_abm'.")
    name: str
    spec_layer: str = Field(description="Which SPEC §7 forecast layer this represents.")
    approach: str = Field(description="One-line description of the method.")
    central_pct: float = Field(description="Central estimate of the % reduction (negative = fall).")
    low_pct: float = Field(description="Low edge of this method's own range.")
    high_pct: float = Field(description="High edge of this method's own range.")
    weight: float = Field(ge=0.0, le=1.0, description="Ensemble weight for this method.")
    applicable: bool = Field(
        default=True,
        description="False when the method does not fit this intervention (weight→0).",
    )
    tag: MetricTag = Field(description="Provenance of this method's estimate.")
    assumptions: list[str] = Field(default_factory=list)
    note: str = Field(default="")


class EnsembleMetric(BaseModel):
    """The pooled ensemble estimate for one metric with a disagreement signal."""

    metric_key: str
    label: str
    unit: str = Field(default="% vs baseline")
    horizon: Checkpoint
    methods: list[MethodEstimate] = Field(default_factory=list)
    ensemble_central_pct: float = Field(description="Weighted central estimate.")
    ensemble_low_pct: float = Field(description="Low edge spanning method disagreement.")
    ensemble_high_pct: float = Field(description="High edge spanning method disagreement.")
    method_spread_pct: float = Field(
        description="max(central) − min(central) across applicable methods — raw disagreement."
    )
    disagreement: str = Field(description="'low' | 'moderate' | 'high' agreement label.")
    tag: MetricTag = Field(
        MetricTag.estimated,
        description="A cross-method blend is Estimated, not a single Simulated run.",
    )
    interpretation: str = Field(default="")


class EnsembleForecast(BaseModel):
    """Ensemble forecast payload for a policy run (SPEC §8)."""

    provenance: MetricTag = Field(MetricTag.estimated)
    note: str = Field(
        default=(
            "Ensemble forecast: the flagship cordon effect estimated by three "
            "independent methods (agent-based, historical-analogue transfer, "
            "reduced-form elasticity) and pooled with documented weights. The band "
            "spans method disagreement — wide bands mean the methods disagree, not "
            "false precision (SPEC §8). No LLM touches any number (SPEC §34)."
        )
    )
    policy_id: str
    horizon: Checkpoint
    metrics: list[EnsembleMetric] = Field(default_factory=list)
    method_weights: dict = Field(
        default_factory=dict, description="Documented ensemble weights by method (auditable)."
    )
