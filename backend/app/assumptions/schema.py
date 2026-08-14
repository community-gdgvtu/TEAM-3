"""Response schema for the change-assumptions-and-rerun endpoint (SPEC §34.10)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..baseline.schema import BaselineMetrics, Checkpoint, MetricTag
from ..simulation.schema import DeltaTimeSeries, WorldBMetrics


class AppliedOverride(BaseModel):
    """One assumption override, echoed with what was actually applied."""

    name: str
    label: str
    unit: str = ""
    default: float = Field(description="Live default value for this assumption.")
    low: float
    high: float
    requested: float = Field(description="The value the caller asked for.")
    applied: float = Field(description="The value actually used (clamped to range).")
    in_range: bool = Field(description="Whether `requested` was within [low, high].")
    clamped: bool = Field(description="True when `applied` differs from `requested`.")
    note: str = ""


class MetricContrast(BaseModel):
    """How overriding the assumptions moved one metric's Δ at the horizon."""

    key: str
    label: str
    unit: str
    default_delta: float = Field(description="Δ(B−A) under default assumptions.")
    overridden_delta: float = Field(description="Δ(B−A) under the overridden assumptions.")
    shift: float = Field(description="overridden_delta − default_delta (effect of the change).")
    shift_pct_of_default: Optional[float] = Field(
        default=None,
        description="`shift` as % of |default_delta| (None when the default is ~0).",
    )


class AssumptionRerunResponse(BaseModel):
    """World A/B/Δ re-run under user-pinned assumptions, contrasted vs defaults."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Deterministic A/B/Δ re-run with the listed input assumptions overridden "
            "(SPEC §34.10 — users can change assumptions and rerun). No new model and "
            "no LLM on the numeric path (SPEC §34); the overridable knobs are the same "
            "assumptions the §24 uncertainty engine sweeps."
        )
    )
    policy_id: str
    horizon: Checkpoint = Field(description="Horizon the contrast is reported at.")
    overrides: list[AppliedOverride] = Field(
        default_factory=list, description="Every requested override + what was applied."
    )
    contrast: list[MetricContrast] = Field(
        default_factory=list,
        description="Per-metric Δ under defaults vs overrides at the horizon.",
    )
    world_a_snapshot: BaselineMetrics
    world_b_snapshot: WorldBMetrics
    delta: DeltaTimeSeries = Field(
        description="Full Δ(B−A) trajectory under the overridden assumptions (replot-ready)."
    )
    shocks_applied: dict = Field(default_factory=dict)
