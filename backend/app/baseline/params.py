"""Transparent baseline (World A) modelling assumptions.

Every number here is an **input assumption**, not an observed record and not an
LLM output. They parameterise the deterministic agent-based mode-choice model in
:mod:`app.baseline.model`. Keeping them in one place (with rationale) makes the
baseline auditable — the Evidence Drawer (SPEC §26) can surface exactly which
assumption fed which metric, and a human can correct any of them.

Guardrail (SPEC §34): these constants and the model that consumes them produce
the core numeric baseline. No LLM is involved in the numeric path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BaselineParams:
    """Assumptions for the World-A (no-intervention) commuter model."""

    # --- Feasibility / speeds (km/h) ---------------------------------------
    walk_max_km: float = 2.0  # trips longer than this are not walked
    walk_speed_kmh: float = 4.8
    car_speed_cbd_kmh: float = 18.0  # congested central speed
    car_speed_kmh: float = 26.0  # non-central road speed
    transit_speed_kmh: float = 15.0  # effective incl. stops/dwell

    # --- Access / egress overheads (minutes per one-way trip) --------------
    car_overhead_min: float = 6.0  # parking search + walk from parking
    transit_overhead_min: float = 8.0  # walk to stop + wait

    # --- Monetary cost per one-way trip (local currency units) -------------
    car_cost_per_km: float = 0.25  # fuel + wear
    transit_fare: float = 1.80  # flat fare

    # --- Generalized-cost weighting ----------------------------------------
    # Money is converted to minutes-equivalent so a single generalized cost can
    # be minimised. The per-agent ``price_sensitivity`` (0..1) scales it, so
    # lower-income / price-sensitive agents feel money more heavily.
    money_to_minutes: float = 8.0  # minutes of disutility per currency unit

    # --- Aggregation factors ------------------------------------------------
    trips_per_commuter_per_day: int = 2  # outbound + return
    workdays_per_year: int = 250

    # --- Emissions proxy ----------------------------------------------------
    # Average tailpipe CO2 for a petrol car (kg per vehicle-km). Estimated
    # input; the resulting totals are Simulated (factor × modelled vehicle-km).
    car_co2_kg_per_km: float = 0.192

    def as_dict(self) -> dict:
        return asdict(self)


#: The default baseline assumption set used unless a caller overrides it.
DEFAULT_PARAMS = BaselineParams()
