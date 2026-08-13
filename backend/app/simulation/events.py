"""Derive the structured event ledger from a simulation run (ROADMAP M3, SPEC §10).

Every meaningful change in the World-A → World-B trajectory becomes a structured
:class:`~app.simulation.schema.LedgerEvent`: a mode shift, a cordon-load drop, a
transit-capacity breach, an emissions milestone, the revenue-funded transit
ramp. Events fire at the *earliest* Time Machine checkpoint where their threshold
is crossed, carry the modelled ``affected_agents`` count, a horizon-decaying
``confidence`` and their ``cause``/``downstream`` links.

This ledger is the shared truth SPEC §10 mandates: the parliament, opinion model,
press simulation and red team all read it, and generated narratives may cite
these events but must never invent quantitative events absent here.

Guardrail (SPEC §34): every number is read straight from the deterministic
model's Δ(B−A) output — no LLM — so the ledger is tagged Simulated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from ..baseline.schema import BaselineMetrics
from ..policy.dsl import InterventionType, PolicyDSL
from .schema import DeltaSeries, DeltaTimeSeries, EventLedger, LedgerEvent


@dataclass(frozen=True)
class EventThresholds:
    """Transparent detection thresholds for the ledger (auditable input assumptions)."""

    #: Baseline peak transit capacity as a multiple of current peak CBD-bound
    #: transit demand (network sized ~15% above today's peak).
    transit_capacity_headroom: float = 1.15
    #: Car mode-share drop (percentage points) that counts as a material mode shift.
    material_mode_shift_pp: float = 3.0
    #: Cordon vehicle-trip drop (%) that counts as a material cordon-load drop.
    material_cordon_drop_pct: float = 10.0
    #: Commute CO₂ drop (%) that counts as an emissions milestone.
    material_emissions_drop_pct: float = 10.0
    #: Transit-ramp uplift (% more boardings vs the short-run level) that flags
    #: the revenue-funded reinvestment as having landed.
    material_transit_ramp_pct: float = 5.0
    #: Confidence at T0 and how fast it decays per year (SPEC §24).
    confidence_base: float = 0.9
    confidence_decay_per_year: float = 0.05
    confidence_floor: float = 0.35

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_THRESHOLDS = EventThresholds()

_PRICING_TYPES = {
    InterventionType.road_pricing,
    InterventionType.parking_levy,
    InterventionType.low_emission_zone,
}


def _series_index(delta: DeltaTimeSeries) -> dict[str, DeltaSeries]:
    return {s.key: s for s in delta.series}


def _confidence(years: float, th: EventThresholds) -> float:
    return round(
        max(th.confidence_floor, th.confidence_base - th.confidence_decay_per_year * years),
        2,
    )


def _timestamp(policy: PolicyDSL, months: float) -> str | None:
    """implementation_date + ``months`` as an ISO date, if a start date is known."""
    iso = policy.intervention.implementation_date
    if not iso:
        return None
    try:
        start = date.fromisoformat(iso)
    except ValueError:
        return None
    return (start + timedelta(days=round(months * 30.4375))).isoformat()


def _severity(magnitude_pct: float) -> str:
    m = abs(magnitude_pct)
    if m >= 25.0:
        return "critical"
    if m >= 10.0:
        return "notable"
    return "info"


def _primary_cause(policy: PolicyDSL) -> str:
    itype = policy.intervention.type
    if itype == InterventionType.pedestrianisation:
        return "pedestrianisation"
    if itype in _PRICING_TYPES:
        return "cordon_charge"
    return itype.value


def build_event_ledger(
    policy: PolicyDSL,
    world_a: BaselineMetrics,
    delta: DeltaTimeSeries,
    thresholds: EventThresholds = DEFAULT_THRESHOLDS,
) -> EventLedger:
    """Build the deterministic event ledger from a run's Δ(B−A) trajectory."""
    idx = _series_index(delta)
    cps = delta.checkpoints
    cause0 = _primary_cause(policy)
    events: list[LedgerEvent] = []

    def emit(ev: LedgerEvent) -> None:
        events.append(ev)

    # --- 1. Mode shift (earliest checkpoint car share drops materially) -----
    car = idx.get("mode_share.car_pct")
    if car is not None:
        for cp, p in zip(cps, car.points):
            if p.delta <= -thresholds.material_mode_shift_pp:
                affected = round(abs(p.delta) / 100.0 * world_a.commuters)
                emit(
                    LedgerEvent(
                        id="ev_mode_shift",
                        type="mode_shift",
                        scenario_month=cp.t_months,
                        scenario_year=cp.t_years,
                        timestamp=_timestamp(policy, cp.t_months),
                        description=(
                            f"Car mode share falls {abs(p.delta):.1f}pp "
                            f"({p.world_a:.1f}% → {p.world_b:.1f}%) as commuters "
                            "substitute away from the charged/banned car trip."
                        ),
                        cause=[cause0, "generalized_cost_increase"],
                        affected_agents=affected,
                        confidence=_confidence(cp.t_years, thresholds),
                        downstream=["transit_demand", "congestion", "emissions"],
                        severity=_severity(p.delta),
                        evidence={"mode_share.car_pct": {"world_a": p.world_a, "world_b": p.world_b, "delta": p.delta}},
                    )
                )
                break

    # --- 2. Cordon-load drop ------------------------------------------------
    cordon = idx.get("traffic.vehicle_trips_into_cbd")
    if cordon is not None:
        for cp, p in zip(cps, cordon.points):
            if p.delta_pct is not None and p.delta_pct <= -thresholds.material_cordon_drop_pct:
                emit(
                    LedgerEvent(
                        id="ev_cordon_load_drop",
                        type="cordon_load",
                        scenario_month=cp.t_months,
                        scenario_year=cp.t_years,
                        timestamp=_timestamp(policy, cp.t_months),
                        description=(
                            f"CBD-bound vehicle trips drop {abs(p.delta_pct):.0f}% "
                            f"({p.world_a:.0f} → {p.world_b:.0f} trips/day) inside the cordon."
                        ),
                        cause=[cause0],
                        affected_agents=round(abs(p.delta) / 2.0),  # trips → commuters
                        confidence=_confidence(cp.t_years, thresholds),
                        downstream=["congestion", "air_quality", "retail_footfall"],
                        severity=_severity(p.delta_pct),
                        evidence={"traffic.vehicle_trips_into_cbd": {"world_a": p.world_a, "world_b": p.world_b, "delta_pct": p.delta_pct}},
                    )
                )
                break

    # --- 3. Transit-capacity breach (SPEC §10 canonical example) ------------
    peak = idx.get("transit.peak_into_cbd_transit_trips")
    if peak is not None and peak.points:
        capacity = peak.points[0].world_a * thresholds.transit_capacity_headroom
        for cp, p in zip(cps, peak.points):
            if p.world_b > capacity:
                over = round(p.world_b - capacity)
                emit(
                    LedgerEvent(
                        id="ev_transit_capacity",
                        type="transit_capacity",
                        scenario_month=cp.t_months,
                        scenario_year=cp.t_years,
                        timestamp=_timestamp(policy, cp.t_months),
                        description=(
                            "Peak CBD-bound transit demand exceeds baseline capacity "
                            f"({p.world_b:.0f} vs ~{capacity:.0f} trips/day headroom)."
                        ),
                        cause=[cause0, "mode_shift"],
                        affected_agents=max(0, over),
                        confidence=_confidence(cp.t_years, thresholds),
                        downstream=["crowding", "commute_delay", "public_sentiment"],
                        severity="notable",
                        evidence={
                            "transit.peak_into_cbd_transit_trips": {"world_b": p.world_b, "baseline_capacity": round(capacity)},
                            "transit_capacity_headroom": thresholds.transit_capacity_headroom,
                        },
                    )
                )
                break

    # --- 4. Emissions milestone ---------------------------------------------
    co2 = idx.get("emissions.daily_co2_tonnes")
    if co2 is not None:
        for cp, p in zip(cps, co2.points):
            if p.delta_pct is not None and p.delta_pct <= -thresholds.material_emissions_drop_pct:
                emit(
                    LedgerEvent(
                        id="ev_emissions_milestone",
                        type="emissions",
                        scenario_month=cp.t_months,
                        scenario_year=cp.t_years,
                        timestamp=_timestamp(policy, cp.t_months),
                        description=(
                            f"Daily commute CO₂ falls {abs(p.delta_pct):.0f}% "
                            f"({p.world_a:.2f} → {p.world_b:.2f} tCO₂/day)."
                        ),
                        cause=[cause0, "mode_shift"],
                        affected_agents=0,
                        confidence=_confidence(cp.t_years, thresholds),
                        downstream=["air_quality", "health", "climate_targets"],
                        severity=_severity(p.delta_pct),
                        evidence={"emissions.daily_co2_tonnes": {"world_a": p.world_a, "world_b": p.world_b, "delta_pct": p.delta_pct}},
                    )
                )
                break

    # --- 5. Revenue-funded transit ramp landing -----------------------------
    # The mid-run reinvestment is isolated by comparing boardings against the
    # *short-run plateau* (the last checkpoint before the ~6-month capacity lag),
    # where behavioural substitution is essentially complete but the ramp has not
    # landed. Extra boardings beyond that plateau are the revenue-funded ramp —
    # not the day-one mode shift.
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)
    boardings = idx.get("transit.daily_transit_trips")
    if pt_share > 0.0 and boardings is not None and boardings.points:
        plateau_idx = max(
            (i for i, cp in enumerate(cps) if cp.t_months <= 5.0), default=0
        )
        short_run = boardings.points[plateau_idx].world_b
        for cp, p in list(zip(cps, boardings.points))[plateau_idx + 1 :]:
            if short_run <= 0:
                continue
            uplift_pct = 100.0 * (p.world_b - short_run) / short_run
            if uplift_pct >= thresholds.material_transit_ramp_pct:
                emit(
                    LedgerEvent(
                        id="ev_transit_reinvestment",
                        type="transit_reinvestment",
                        scenario_month=cp.t_months,
                        scenario_year=cp.t_years,
                        timestamp=_timestamp(policy, cp.t_months),
                        description=(
                            f"Revenue-funded transit capacity ramp lands: boardings "
                            f"up {uplift_pct:.0f}% vs the short-run level as cheaper/"
                            "faster service pulls more commuters onto transit."
                        ),
                        cause=[cause0, "revenue_reinvestment"],
                        affected_agents=round((p.world_b - short_run) / 2.0),
                        confidence=_confidence(cp.t_years, thresholds),
                        downstream=["transit_speed", "transit_fare", "mode_shift"],
                        severity="info",
                        evidence={"transit.daily_transit_trips": {"short_run": round(short_run), "world_b": round(p.world_b), "uplift_pct": round(uplift_pct, 1)}, "revenue_allocation.public_transport": pt_share},
                    )
                )
                break

    events.sort(key=lambda e: (e.scenario_month, e.id))
    return EventLedger(
        policy_id=policy.id,
        events=events,
        thresholds=thresholds.as_dict(),
    )
