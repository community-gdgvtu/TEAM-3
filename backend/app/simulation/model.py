"""Deterministic agent-based World-B mode-choice + traffic model (ROADMAP M3).

Given a compiled :class:`~app.policy.dsl.PolicyDSL`, this recomputes each
commuter's travel mode under the intervention and re-aggregates the same four
headline metric families as the baseline (mode share / traffic / emissions proxy
/ transit demand). It is the *policy* counterpart of
:func:`app.baseline.model.compute_baseline` and shares its generalized-cost
machinery so World A and World B are strictly comparable.

Guardrails (SPEC §34):

* Deterministic and LLM-free — same population + same policy ⇒ identical numbers.
* The policy is applied only through the explicit levers in
  :mod:`app.simulation.levers` (a cordon charge, a car ban, a transit service
  uplift). Nothing else about an agent changes.
* Every headline number is emitted as a provenance-tagged :class:`Metric`
  (Simulated), and the engaged behavioural rules are surfaced for the Evidence
  Drawer (SPEC §7.5/§26).
"""

from __future__ import annotations

from .. import dataset
from ..baseline.model import CAR, TRANSIT, WALK, _one_way_minutes, _round, pick_mode
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.schema import (
    EmissionsMetrics,
    Metric,
    MetricTag,
    ModeShare,
    TrafficMetrics,
    TransitMetrics,
)
from ..policy.dsl import PolicyDSL
from .levers import DEFAULT_SIM_PARAMS, PolicyLevers, SimParams, derive_levers
from .schema import WorldBMetrics


def policy_mode_options(
    agent: dict,
    levers: PolicyLevers,
    cbd_zone_ids: set[str],
    params: BaselineParams = DEFAULT_PARAMS,
) -> dict[str, float]:
    """Generalized cost of each feasible mode under the policy.

    Identical to :func:`app.baseline.model.mode_options` except that the compiled
    policy's levers modify the car and transit options:

    * a CBD-bound, non-exempt car trip pays ``charge_per_one_way`` extra money;
    * under pedestrianisation the car option is removed for CBD-bound commuters;
    * transit fare and effective speed are scaled by the reinvestment multipliers.

    Walking is untouched. As in the baseline, every agent has car *or* transit
    access, and a car ban only applies to CBD-bound trips, so a feasible mode
    always remains.
    """
    dist = agent["commute_distance_km"]
    price_sens = agent["price_sensitivity"]
    into_cbd = agent["commutes_into_cbd"]

    options: dict[str, float] = {}

    if dist <= params.walk_max_km:
        options[WALK] = _one_way_minutes(dist, params.walk_speed_kmh, 0.0)

    car_available = agent["car_access"] and not (into_cbd and levers.car_banned_in_cbd)
    if car_available:
        car_speed = params.car_speed_cbd_kmh if into_cbd else params.car_speed_kmh
        time_min = _one_way_minutes(dist, car_speed, params.car_overhead_min)
        money = dist * params.car_cost_per_km
        if into_cbd and levers.charge_per_one_way > 0 and not levers.is_exempt(
            agent, cbd_zone_ids
        ):
            money += levers.charge_per_one_way
        options[CAR] = time_min + price_sens * params.money_to_minutes * money

    if agent["public_transit_access"]:
        transit_speed = params.transit_speed_kmh * levers.transit_speed_multiplier
        time_min = _one_way_minutes(dist, transit_speed, params.transit_overhead_min)
        money = params.transit_fare * levers.transit_fare_multiplier
        options[TRANSIT] = time_min + price_sens * params.money_to_minutes * money

    if not options:
        # Park-and-walk fallback: a CBD-bound car-only commuter with no transit
        # access and a trip too long to walk normally cannot drive into a
        # pedestrianised core. Rather than strand them, they drive to the cordon
        # edge and complete the trip on foot — counted as walk (they no longer
        # enter the CBD by car). This only fires under the pedestrianisation ban.
        options[WALK] = _one_way_minutes(dist, params.walk_speed_kmh, 0.0)

    return options


def choose_mode_policy(
    agent: dict,
    levers: PolicyLevers,
    cbd_zone_ids: set[str],
    params: BaselineParams = DEFAULT_PARAMS,
) -> str:
    """Pick a commuter's travel mode under the policy (argmin generalized cost)."""
    return pick_mode(policy_mode_options(agent, levers, cbd_zone_ids, params))


def compute_world_b(
    policy: PolicyDSL,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    reinvestment: bool = True,
) -> WorldBMetrics:
    """Run the policy mode-choice model over the whole synthetic population.

    Returns a fully provenance-tagged :class:`WorldBMetrics` snapshot — the
    with-intervention counterpart to the baseline. The behavioural levers derived
    from ``policy`` are attached for the Evidence Drawer (SPEC §7.5).

    ``reinvestment`` gates the revenue → transit service uplift. Set it ``False``
    to obtain the *short-run* reachable state (people substitute away from the
    charge/ban immediately, but the revenue-funded transit capacity ramp has not
    yet landed). The timeline builder (:mod:`app.simulation.timeline`) uses both
    the reinvestment-off and reinvestment-on anchors to stage adaptation over the
    Time Machine horizon (SPEC §9).
    """
    agents = dataset.population_agents()
    cbd_zone_ids = dataset.cbd_zone_ids()
    levers = derive_levers(policy, params=params, sim=sim)
    if not reinvestment:
        # Short-run anchor: the behavioural substitution has happened, but the
        # transit capacity funded by revenue has not been built yet, so the
        # service-quality levers are neutral and their audit rule is dropped.
        levers.transit_fare_multiplier = 1.0
        levers.transit_speed_multiplier = 1.0
        levers.rules = [r for r in levers.rules if r.name != "transit_reinvestment"]
    trips = params.trips_per_commuter_per_day

    counts = {CAR: 0, TRANSIT: 0, WALK: 0}
    car_km_one_way = 0.0
    car_commute_min_sum = 0.0
    vehicle_trips_into_cbd = 0
    transit_km_one_way = 0.0
    peak_into_cbd_transit = 0
    priced_car_commuters = 0

    for a in agents:
        mode = choose_mode_policy(a, levers, cbd_zone_ids, params)
        counts[mode] += 1
        dist = a["commute_distance_km"]
        if mode == CAR:
            car_km_one_way += dist
            car_commute_min_sum += a["baseline_commute_minutes"]
            if a["commutes_into_cbd"]:
                vehicle_trips_into_cbd += 1
                if levers.charge_per_one_way > 0 and not levers.is_exempt(
                    a, cbd_zone_ids
                ):
                    priced_car_commuters += 1
        elif mode == TRANSIT:
            transit_km_one_way += dist
            if a["commutes_into_cbd"]:
                peak_into_cbd_transit += 1

    total = len(agents)
    pct = lambda n: _round(100.0 * n / total, 1) if total else 0.0

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
            method="Share of commuters whose min-generalized-cost mode is car, under the policy.",
            assumptions=["car_speed_kmh", "car_cost_per_km", "cordon_charge"],
        ),
        Metric(
            key="mode_share.public_transit_pct",
            label="Public-transit mode share",
            value=mode_share.public_transit_pct,
            unit="%",
            tag=MetricTag.simulated,
            method="Share of commuters whose min-generalized-cost mode is transit, under the policy.",
            assumptions=["transit_fare", "transit_speed_kmh", "transit_reinvestment"],
        ),
        Metric(
            key="mode_share.walk_pct",
            label="Walk mode share",
            value=mode_share.walk_pct,
            unit="%",
            tag=MetricTag.simulated,
            method="Share of commuters who walk under the policy.",
            assumptions=["walk_max_km", "walk_speed_kmh"],
        ),
        Metric(
            key="traffic.daily_vehicle_km",
            label="Daily vehicle-km",
            value=traffic.daily_vehicle_km,
            unit="veh-km/day",
            tag=MetricTag.simulated,
            method="Σ car-commuter distance × trips/day, after policy mode switching.",
            assumptions=["trips_per_commuter_per_day", "cordon_charge", "pedestrianisation"],
        ),
        Metric(
            key="traffic.vehicle_trips_into_cbd",
            label="Vehicle trips into CBD",
            value=float(traffic.vehicle_trips_into_cbd),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Car commuters still driving into the priced/pedestrianised CBD × trips/day.",
            assumptions=["cordon_charge", "pedestrianisation"],
        ),
        Metric(
            key="emissions.daily_co2_tonnes",
            label="Daily commute CO₂",
            value=emissions.daily_co2_tonnes,
            unit="tCO₂/day",
            tag=MetricTag.simulated,
            method="Policy vehicle-km × car_co2_kg_per_km (emissions proxy).",
            assumptions=["car_co2_kg_per_km"],
        ),
        Metric(
            key="transit.daily_transit_trips",
            label="Daily transit boardings",
            value=float(transit.daily_transit_trips),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Transit-mode commuters under the policy × trips/day.",
            assumptions=["trips_per_commuter_per_day", "transit_reinvestment"],
        ),
        Metric(
            key="transit.peak_into_cbd_transit_trips",
            label="Peak CBD-bound transit demand",
            value=float(transit.peak_into_cbd_transit_trips),
            unit="trips/day",
            tag=MetricTag.simulated,
            method="Transit commuters working in the CBD under the policy × trips/day.",
            assumptions=["trips_per_commuter_per_day"],
        ),
    ]

    return WorldBMetrics(
        policy_id=policy.id,
        population_agents=total,
        commuters=total,
        mode_share=mode_share,
        traffic=traffic,
        emissions=emissions,
        transit=transit,
        priced_car_commuters=priced_car_commuters,
        daily_priced_entries=priced_car_commuters * trips,
        metrics=metrics,
        behavioural_rules=levers.rules,
        levers=levers.as_dict(),
        params=sim.as_dict(),
    )
