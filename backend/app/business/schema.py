"""Pydantic schemas for the Business View (SPEC §17 Business View)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FirmProfile(BaseModel):
    """The static profile of one synthetic firm (SPEC §17 "Click a firm")."""

    firm_id: str = Field(description="Stable synthetic firm id, e.g. 'FIRM-0421'.")
    sector: str = Field(description="Business sector inferred from the building kind.")
    building_kind: str = Field(description="Raw building kind (office/tower/podium/lowrise/mixed/industrial).")
    zone_id: str
    in_central_district: bool = Field(description="Whether the firm sits inside the priced/central district.")
    floors: int = Field(description="Estimated storeys (height ÷ storey height).")
    floor_area_sqm: float = Field(description="Estimated gross floor area (footprint × floors).")
    estimated_jobs: int = Field(
        description="Jobs allocated to this firm from its zone's total, by floor-space share."
    )
    provenance: str = Field(
        default="Simulated — synthetic building/firm (SPEC §6); jobs allocated by floor-space share (Estimated).",
    )


class FirmSnapshot(BaseModel):
    """This firm's operating picture at one Time-Machine checkpoint (SPEC §17)."""

    label: str = Field(description="Checkpoint label, e.g. 'BEFORE POLICY', '5 months', '2 years'.")
    t_months: float
    daily_footfall: float = Field(description="Worker + customer daily footfall at the firm.")
    daily_footfall_low: float
    daily_footfall_high: float
    labour_accessibility_index: float = Field(
        description="100 = baseline ease of reaching the firm for its workers; <100 = worse (higher commute cost)."
    )
    daily_deliveries: float = Field(description="Delivery/freight vehicle trips serving the firm per day.")
    annual_cost_added: float = Field(description="Added annual firm operating cost (delivery-charge pass-through).")
    annual_cost_added_low: float
    annual_cost_added_high: float
    revenue_proxy_annual: float = Field(description="Footfall × spend proxy (Estimated; ratio-meaningful only).")
    revenue_proxy_annual_low: float
    revenue_proxy_annual_high: float
    net_revenue_proxy_change_pct: float = Field(
        description="Net revenue proxy change vs baseline after added costs (%)."
    )


class BusinessView(BaseModel):
    """Full Business View for one firm under a policy (SPEC §17 Business View).

    Deterministic and LLM-free (SPEC §34). Labour accessibility comes from the
    *same* deterministic mode-choice model as ``/simulate`` (the commute
    generalized cost of the firm's own workers); footfall / deliveries / costs /
    revenue reuse the *same* economic coefficients as ``/economy`` (charge,
    freight share, avoidance fraction, pedestrianisation uplift), staged across
    the horizon with the *same* adaptation curve as the aggregate Time Machine —
    so a firm's numbers can never disagree with the dashboard beside them.
    """

    policy_id: str
    selector: str = Field(description="How this firm was chosen (firm_id / representative / ...).")
    profile: FirmProfile
    before_policy: FirmSnapshot = Field(description="World-A (no-intervention) reference (SPEC §17).")
    trajectory: list[FirmSnapshot] = Field(
        description="The firm's operating picture across the Time-Machine checkpoints (T0 → 10y)."
    )
    adaptation_decisions: list[str] = Field(
        description="Deterministic firm adaptation responses implied by its exposure (SPEC §17)."
    )
    headline: str = Field(description="One-line human summary of the change for this firm.")
    explanation: list[str] = Field(
        description="Deterministic 'Why?' narrative tied to the staged model (SPEC §17)."
    )
    provenance: str = Field(
        default=(
            "Simulated physical drivers (mode-shift, cordon entries; SPEC §7.3/§7.5) → "
            "Estimated firm translation (footfall/deliveries/revenue; SPEC §7.4/§8), staged "
            "over the Time Machine (SPEC §9). No LLM in the numeric path (SPEC §34)."
        ),
    )
    not_modelled: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)


class FirmSample(BaseModel):
    """A lightweight, policy-independent firm card for a UI picker (SPEC §17)."""

    firm_id: str
    label: str
    sector: str
    zone_id: str
    in_central_district: bool
    estimated_jobs: int
    provenance: str = Field(default="Simulated — synthetic firm (SPEC §6).")
