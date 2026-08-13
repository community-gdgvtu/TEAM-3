"""Response schema for the global one-at-a-time sensitivity ("tornado") layer.

SPEC §24 (uncertainty) + §26 (explainability). This layer answers the minister's
question — *"which of your assumptions is the answer actually resting on?"* —
across **every** headline metric at once, not just one. Every number is a re-run
of the deterministic World-A/B/Δ model at a documented assumption's plausible
low/high edge, so nothing here is an LLM output (SPEC §34); the analysis itself
is tagged Estimated (it is an attribution derived from the model, not observed
data).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class AssumptionSwing(BaseModel):
    """How far one metric's policy effect (Δ) moves when one assumption is swept
    from its documented low edge to its documented high edge (others held at
    default) — one bar of a tornado chart."""

    name: str = Field(description="Stable assumption key (matches GET /assumptions).")
    label: str = Field(description="Human-readable assumption name.")
    unit: str = Field(default="", description="Unit of the assumption value.")
    low_value: float = Field(description="Assumption value at the low edge of its range.")
    high_value: float = Field(description="Assumption value at the high edge of its range.")
    delta_at_low: float = Field(description="Metric Δ(B−A) with the assumption at its low edge.")
    delta_at_high: float = Field(description="Metric Δ(B−A) with the assumption at its high edge.")
    swing: float = Field(
        description="Signed high−low change in the metric's Δ (sign = which way the "
        "high edge pushes the effect)."
    )
    abs_swing: float = Field(description="|swing| — the bar length for ranking.")
    pct_of_default: float | None = Field(
        default=None,
        description="|swing| as % of the default-assumption Δ (None when that Δ ≈ 0).",
    )
    influence_share: float = Field(
        description="This assumption's share (0–1) of the total sensitivity of THIS "
        "metric across all swept assumptions — a scale-free leverage measure."
    )
    direction: str = Field(description="'up' | 'down' | 'flat' — sign of high−low.")


class MetricTornado(BaseModel):
    """One headline metric's tornado: its default policy effect plus every
    assumption's swing around it, ranked by leverage."""

    key: str = Field(description="Metric key, e.g. 'traffic.vehicle_trips_into_cbd'.")
    label: str
    unit: str
    tag: MetricTag = Field(
        MetricTag.simulated, description="Provenance of the underlying Δ metric."
    )
    default_delta: float = Field(
        description="The metric's policy effect Δ(B−A) at the default assumptions."
    )
    total_abs_swing: float = Field(
        description="Sum of |swing| over all assumptions — the metric's total OAT sensitivity."
    )
    most_influential: str | None = Field(
        default=None, description="Name of the assumption with the largest |swing| (None if all flat)."
    )
    bars: list[AssumptionSwing] = Field(
        default_factory=list, description="Per-assumption swings, ranked most→least influential."
    )


class AssumptionDriver(BaseModel):
    """One assumption's aggregate leverage across the whole dashboard."""

    name: str
    label: str
    unit: str = ""
    global_score: float = Field(
        description="Mean influence_share across all metrics (0–1) — how much of the "
        "dashboard's total sensitivity this one assumption carries."
    )
    max_pct_of_default: float | None = Field(
        default=None,
        description="Largest |swing| as % of default Δ over any metric (None when undefined).",
    )
    top_metric: str | None = Field(
        default=None, description="Metric key this assumption moves most (by |swing| share)."
    )
    matters: bool = Field(
        description="False when this assumption is flat on every metric for this policy "
        "(e.g. a fare-cut assumption under a no-charge policy) — honestly surfaced."
    )
    note: str = Field(default="", description="Plain-language leverage interpretation.")


class SensitivityResult(BaseModel):
    """Global one-at-a-time sensitivity tornado across all headline metrics."""

    provenance: MetricTag = Field(
        MetricTag.estimated,
        description="Sensitivity attribution derived from the deterministic model at "
        "documented assumption ranges — Estimated, not observed (SPEC §34).",
    )
    note: str = Field(
        default=(
            "One-at-a-time sensitivity: each documented assumption is swept from its "
            "plausible low to high edge (others held at default) and the resulting "
            "swing in every headline metric's policy effect Δ(B−A) is measured. Bar "
            "length = leverage, not likelihood; interactions between assumptions are "
            "NOT captured here (that is what the §24 Monte-Carlo fan on /uncertainty "
            "does). Deterministic, no LLM (SPEC §24/§26/§34)."
        )
    )
    policy_id: str
    horizon: Checkpoint
    swept_assumptions: list[str] = Field(
        default_factory=list, description="Assumption keys swept (same set as /uncertainty)."
    )
    drivers: list[AssumptionDriver] = Field(
        default_factory=list,
        description="Assumptions ranked by aggregate dashboard leverage (most→least).",
    )
    tornados: list[MetricTornado] = Field(
        default_factory=list, description="Per-metric tornado charts."
    )
    headline: str = Field(
        description="One-sentence plain-language read of what the answer rests on."
    )
    not_modelled: list[str] = Field(
        default_factory=list, description="Honest scope limits of this OAT analysis (SPEC §34)."
    )
