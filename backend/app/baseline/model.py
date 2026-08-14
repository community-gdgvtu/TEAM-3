"""Deterministic agent-based baseline (World A) mode-choice model + metrics.

This is the *numeric* baseline (SPEC §5): given the synthetic population and city
dataset, assign each commuter a travel mode by minimising a transparent
generalized cost, then aggregate into the four headline families the ROADMAP M2
milestone asks for — mode share, traffic, emissions proxy, transit demand.

Design choices that matter for the guardrails (SPEC §34):

* The model is **deterministic** — no randomness, no LLM. Same population +
  same :class:`~app.baseline.params.BaselineParams` ⇒ identical numbers.
* Every headline number is emitted as a provenance-tagged :class:`Metric`
  (Simulated, because it is produced by this structural model — SPEC §8).
* Policy responses (a congestion charge, pedestrianisation) are **not** applied
  here; World A is the no-intervention reference. Deltas come later in M3.
"""

from __future__ import annotations

from functools import lru_cache

from .. import dataset
from .params import DEFAULT_PARAMS, BaselineParams
from .schema import (
    BaselineMetrics,
    EmissionsMetrics,
    Metric,
    MetricTag,
    ModeShare,
    TrafficMetrics,
    TransitMetrics,
)

CAR = "car"
TRANSIT = "public_transit"
WALK = "walk"


def _one_way_minutes(distance_km: float, speed_kmh: float, overhead_min: float) -> float:
    """In-vehicle time for ``distance_km`` at ``speed_kmh`` plus fixed overhead."""
    return overhead_min + (distance_km / speed_kmh) * 60.0


def mode_options(agent: dict, params: BaselineParams = DEFAULT_PARAMS) -> dict[str, float]:
    """Generalized cost (minutes-equivalent) of each feasible mode for a commuter.

    Cost is travel time plus the agent's ``price_sensitivity`` applied to the
    monetary cost converted via ``money_to_minutes``. Walking is only feasible for
    short trips and carries no monetary cost. The population invariant (every agent
    has car *or* transit access) guarantees at least one motorised option.
    """
    dist = agent["commute_distance_km"]
    price_sens = agent["price_sensitivity"]
    into_cbd = agent["commutes_into_cbd"]

    options: dict[str, float] = {}

    if dist <= params.walk_max_km:
        # No monetary cost; pure time disutility.
        options[WALK] = _one_way_minutes(dist, params.walk_speed_kmh, 0.0)

    if agent["car_access"]:
        car_speed = params.car_speed_cbd_kmh if into_cbd else params.car_speed_kmh
        time_min = _one_way_minutes(dist, car_speed, params.car_overhead_min)
        money = dist * params.car_cost_per_km
        options[CAR] = time_min + price_sens * params.money_to_minutes * money

    if agent["public_transit_access"]:
        time_min = _one_way_minutes(
            dist, params.transit_speed_kmh, params.transit_overhead_min
        )
        money = params.transit_fare
        options[TRANSIT] = time_min + price_sens * params.money_to_minutes * money

    return options


def pick_mode(options: dict[str, float]) -> str:
    """Deterministic argmin: lowest generalized cost, then a fixed mode order."""
    order = {CAR: 0, TRANSIT: 1, WALK: 2}
    return min(options.items(), key=lambda kv: (kv[1], order[kv[0]]))[0]


def choose_mode(agent: dict, params: BaselineParams = DEFAULT_PARAMS) -> str:
    """Pick the baseline travel mode for one commuter (argmin generalized cost)."""
    return pick_mode(mode_options(agent, params))


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def compute_baseline(params: BaselineParams = DEFAULT_PARAMS) -> BaselineMetrics:
    """Run the baseline model over the whole synthetic population.

    Returns a fully provenance-tagged :class:`BaselineMetrics` snapshot. The
    result is a pure function of the dataset + ``params`` (hence cacheable).
    """
    agents = dataset.population_agents()
    trips = params.trips_per_commuter_per_day

    counts = {CAR: 0, TRANSIT: 0, WALK: 0}
    car_km_one_way = 0.0
    car_commute_min_sum = 0.0
    vehicle_trips_into_cbd = 0
    transit_km_one_way = 0.0
    peak_into_cbd_transit = 0

    for a in agents:
        mode = choose_mode(a, params)
        counts[mode] += 1
        dist = a["commute_distance_km"]
        if mode == CAR:
            car_km_one_way += dist
            car_commute_min_sum += a["baseline_commute_minutes"]
            if a["commutes_into_cbd"]:
                vehicle_trips_into_cbd += 1
        elif mode == TRANSIT:
            transit_km_one_way += dist
            if a["commutes_into_cbd"]:
                peak_into_cbd_transit += 1

    total = len(agents)
    pct = (lambda n: _round(100.0 * n / total, 1) if total else 0.0)

    mode_share = ModeShare(
        car=counts[CAR],
        public_transit=counts[TRANSIT],
        walk=counts[WALK],
        car_pct=pct(counts[CAR]),
        public_transit_pct=pct(counts[TRANSIT]),
        walk_pct=pct(counts[WALK]),
    )

    daily_vehicle_km = car_km_one_way * trips
    daily_transit_pkm = transit_km_one_way * trips
    mean_car_min = _round(car_commute_min_sum / counts[CAR], 1) if counts[CAR] else 0.0

    traffic = TrafficMetrics(
        car_commuters=counts[CAR],
        daily_vehicle_trips=counts[CAR] * trips,
        daily_vehicle_km=_round(daily_vehicle_km),
        vehicle_trips_into_cbd=vehicle_trips_into_cbd * trips,
        mean_car_commute_min=mean_car_min,
    )

    daily_co2_tonnes = daily_vehicle_km * params.car_co2_kg_per_km / 1000.0
    emissions = EmissionsMetrics(
        daily_co2_tonnes=_round(daily_co2_tonnes, 3),
        annual_co2_tonnes=_round(daily_co2_tonnes * params.workdays_per_year, 1),
        co2_kg_per_km=params.car_co2_kg_per_km,
    )

    transit = TransitMetrics(
        transit_commuters=counts[TRANSIT],
        daily_transit_trips=counts[TRANSIT] * trips,
        daily_transit_passenger_km=_round(daily_transit_pkm),
        peak_into_cbd_transit_trips=peak_into_cbd_transit * trips,
    )

    metrics = [
        Metric(
            key="mode_share.car_pct",
            label="Car mode share",
            value=mode_share.car_pct,
            unit="%",
            tag=MetricTag.simulated,
            method="Share of commuters whose min-generalized-cost mode is car.",
            assumptions=["car_speed_kmh", "car_cost_per_km", "money_to_minutes"],
        ),
        Metric(
            key="mode_share.public_transit_pct",
            label="Public-transit mode share",
            value=mode_share.public_transit_pct,
            unit="%",
            tag=MetricTag.simulated,
            method="Share of commuters whose min-generalized-cost mode is transit.",
            assumptions=["transit_speed_kmh", "transit_fare", "transit_overhead_min"],
        ),
        Metric(
            key="mode_share.walk_pct",
            label="Walk mode share",
            value=mode_share.walk_pct,
            unit="%",
            tag=MetricTag.simulated,
            method="Share of short-trip commuters (<= walk_max_km) who walk.",
            assumptions=["walk_max_km", "walk_speed_kmh"],
        ),
        Metric(
            key="traffic.daily_vehicle_km",
            label="Daily vehicle-km",
            value=traffic.daily_vehicle_km,
            unit="veh-km/day",
            tag=MetricTag.simulated,
            method="Σ car-commuter distance × trips_per_commuter_per_day.",
            assumptions=["trips_per_commuter_per_day"],
        ),
        Metric(
            key="traffic.vehicle_trips_into_cbd",
            label="Vehicle trips into CBD",
            value=float(traffic.vehicle_trips_into_cbd),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Car commuters working in the CBD × trips/day (cordon load).",
            assumptions=["trips_per_commuter_per_day"],
        ),
        Metric(
            key="emissions.daily_co2_tonnes",
            label="Daily commute CO₂",
            value=emissions.daily_co2_tonnes,
            unit="tCO₂/day",
            tag=MetricTag.simulated,
            method="Modelled vehicle-km × car_co2_kg_per_km (emissions proxy).",
            assumptions=["car_co2_kg_per_km"],
        ),
        Metric(
            key="transit.daily_transit_trips",
            label="Daily transit boardings",
            value=float(transit.daily_transit_trips),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Transit-mode commuters × trips_per_commuter_per_day.",
            assumptions=["trips_per_commuter_per_day"],
        ),
        Metric(
            key="transit.peak_into_cbd_transit_trips",
            label="Peak CBD-bound transit demand",
            value=float(transit.peak_into_cbd_transit_trips),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Transit commuters working in the CBD × trips/day.",
            assumptions=["trips_per_commuter_per_day"],
        ),
    ]

    return BaselineMetrics(
        population_agents=total,
        commuters=total,
        mode_share=mode_share,
        traffic=traffic,
        emissions=emissions,
        transit=transit,
        metrics=metrics,
        params=params.as_dict(),
    )


@lru_cache(maxsize=1)
def cached_baseline() -> BaselineMetrics:
    """Cached baseline for the default assumptions (dataset is static per run)."""
    return compute_baseline(DEFAULT_PARAMS)


def clear_cache() -> None:
    cached_baseline.cache_clear()
