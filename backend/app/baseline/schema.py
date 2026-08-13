"""Pydantic schemas for the baseline (World A) metrics payload.

The response is designed for two consumers:

* dashboard tiles (mode share / traffic / CO2 / transit), and
* the Evidence Drawer (SPEC §26) — hence every headline number is also emitted
  as a flat :class:`Metric` carrying its provenance ``tag`` (Observed /
  Estimated / Simulated / Generated, SPEC §8) plus the method and assumptions
  that produced it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MetricTag(str, Enum):
    """Provenance class for a single number (SPEC §8 tagging table)."""

    observed = "Observed"
    estimated = "Estimated"
    simulated = "Simulated"
    generated = "Generated"


class Metric(BaseModel):
    """One headline number with full provenance for the Evidence Drawer."""

    key: str = Field(description="Stable machine key, e.g. 'traffic.vehicle_km'.")
    label: str = Field(description="Human-readable label for a dashboard tile.")
    value: float
    unit: str
    tag: MetricTag = Field(description="Observed/Estimated/Simulated/Generated.")
    method: str = Field(description="One-line description of how it was computed.")
    assumptions: list[str] = Field(
        default_factory=list, description="Named input assumptions this number depends on."
    )


class ModeShare(BaseModel):
    """Baseline commuter split across travel modes."""

    car: int = 0
    public_transit: int = 0
    walk: int = 0
    car_pct: float = 0.0
    public_transit_pct: float = 0.0
    walk_pct: float = 0.0


class TrafficMetrics(BaseModel):
    car_commuters: int
    daily_vehicle_trips: int
    daily_vehicle_km: float
    vehicle_trips_into_cbd: int
    mean_car_commute_min: float


class EmissionsMetrics(BaseModel):
    daily_co2_tonnes: float
    annual_co2_tonnes: float
    co2_kg_per_km: float


class TransitMetrics(BaseModel):
    transit_commuters: int
    daily_transit_trips: int
    daily_transit_passenger_km: float
    peak_into_cbd_transit_trips: int


class BaselineMetrics(BaseModel):
    """Full World-A snapshot (no intervention)."""

    world: str = Field("A", description="'A' = baseline, no intervention (SPEC §5).")
    provenance: MetricTag = Field(
        MetricTag.simulated,
        description="Baseline is produced by an agent-based model → Simulated.",
    )
    note: str = Field(
        default=(
            "World A reconstructed by a deterministic agent-based mode-choice "
            "model over the synthetic population. No LLM produced any number "
            "here (SPEC §34)."
        )
    )
    population_agents: int
    commuters: int
    mode_share: ModeShare
    traffic: TrafficMetrics
    emissions: EmissionsMetrics
    transit: TransitMetrics
    metrics: list[Metric] = Field(
        default_factory=list, description="Flat, provenance-tagged headline numbers."
    )
    params: dict = Field(
        default_factory=dict, description="The baseline assumptions used (auditable)."
    )
