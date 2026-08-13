"""Economic spillover model (SPEC §7.4).

Reads the deterministic World-A/World-B mode-choice simulation and translates its
physical outputs into local-economy channels through transparent input-output
relationships and elasticities (:mod:`app.economy.params`):

* **Charge transfer** — cordon revenue withdrawn from household discretionary
  local spending (a transfer, not a loss).
* **Revenue recycling** — that revenue re-spent (transit ops + capital) with a
  local fiscal multiplier; net of the withdrawal this is usually locally positive.
* **CBD footfall** — a small destination-substitution loss from deterred car
  trips, offset by a pedestrianisation retail-amenity uplift (ambiguous sign).
* **Business logistics** — freight/delivery charge cost passed through to CBD
  businesses (Estimated; freight is not agent-modelled).
* **Commuter travel cost** — the private time cost of switching modes to avoid
  the charge/ban, monetised at a value of time consistent with the GC model.

Physical drivers are Simulated; the monetary translation is Estimated (SPEC §8).
Deterministic, no LLM (SPEC §34). Partial-equilibrium and honest about it: the
effects it cannot model are returned in ``not_modelled``.
"""

from __future__ import annotations

from typing import Optional

from .. import dataset
from ..baseline.model import (
    CAR,
    TRANSIT,
    WALK,
    _one_way_minutes,
    compute_baseline,
    mode_options,
    pick_mode,
)
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.schema import Checkpoint, MetricTag
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.levers import DEFAULT_SIM_PARAMS, PolicyLevers, derive_levers
from ..simulation.model import compute_world_b, policy_mode_options
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .params import DEFAULT_ECON_PARAMS, EconParams
from .schema import EconomicChannel, EconomicSpilloverReport, SectorExposure


def _conf_label(c: float) -> str:
    if c >= 0.66:
        return "high"
    if c >= 0.4:
        return "medium"
    return "low"


def _horizon_decay(t_years: float) -> float:
    """Confidence falls with the horizon (SPEC §9/§24): 1.0 now → 0.5 at 10y+."""
    return max(0.5, 1.0 - 0.05 * t_years)


def _chosen_travel_minutes(
    agent: dict,
    mode: str,
    levers: Optional[PolicyLevers],
    into_cbd: bool,
    params: BaselineParams,
) -> float:
    """Pure one-way travel time (minutes) for ``agent`` on ``mode``.

    The *time* component only — money is handled separately by the charge channel
    so the value-of-time channel does not double-count the charge. Mirrors the
    time formulas in the baseline / policy mode-choice models.
    """
    dist = agent["commute_distance_km"]
    if mode == WALK:
        return _one_way_minutes(dist, params.walk_speed_kmh, 0.0)
    if mode == CAR:
        speed = params.car_speed_cbd_kmh if into_cbd else params.car_speed_kmh
        return _one_way_minutes(dist, speed, params.car_overhead_min)
    # TRANSIT — apply the reinvestment speed uplift when present.
    speed_mult = levers.transit_speed_multiplier if levers else 1.0
    return _one_way_minutes(
        dist, params.transit_speed_kmh * speed_mult, params.transit_overhead_min
    )


def _steady_state_flows(
    policy: PolicyDSL, params: BaselineParams
) -> dict[str, float]:
    """Single agent pass → the physical quantities the economic channels read.

    All at the fully-adapted (reinvestment-on) steady state:

    * ``annual_charge_revenue`` — Σ charged entries × charge × workdays,
    * ``delta_commuter_minutes_year`` — Σ change in pure travel minutes from mode
      switches, annualised,
    * ``deterred_cbd_car_commuters`` — commuters who no longer drive into the CBD,
    * ``cbd_commuters`` — commuters whose workplace is in the CBD (footfall base).
    """
    agents = dataset.population_agents()
    cbd_zone_ids = dataset.cbd_zone_ids()
    levers = derive_levers(policy, params=params, sim=DEFAULT_SIM_PARAMS)
    trips = params.trips_per_commuter_per_day
    workdays = params.workdays_per_year

    charge_daily = 0.0
    delta_minutes_daily = 0.0
    base_car_into_cbd = 0
    policy_car_into_cbd = 0
    cbd_commuters = 0

    for a in agents:
        into_cbd = a["commutes_into_cbd"]
        if into_cbd:
            cbd_commuters += 1

        base_mode = pick_mode(mode_options(a, params))
        pol_mode = pick_mode(policy_mode_options(a, levers, cbd_zone_ids, params))

        base_min = _chosen_travel_minutes(a, base_mode, None, into_cbd, params)
        pol_min = _chosen_travel_minutes(a, pol_mode, levers, into_cbd, params)
        # trips/day counts both legs; annualise below.
        delta_minutes_daily += (pol_min - base_min) * trips

        if base_mode == CAR and into_cbd:
            base_car_into_cbd += 1
        if pol_mode == CAR and into_cbd:
            policy_car_into_cbd += 1
            if levers.charge_per_one_way > 0 and not levers.is_exempt(a, cbd_zone_ids):
                # both daily legs cross the cordon
                charge_daily += levers.charge_per_one_way * trips

    return {
        "annual_charge_revenue": charge_daily * workdays,
        "delta_commuter_minutes_year": delta_minutes_daily * workdays,
        "deterred_cbd_car_commuters": float(base_car_into_cbd - policy_car_into_cbd),
        "cbd_commuters": float(cbd_commuters),
        "baseline_cbd_car_commuters": float(base_car_into_cbd),
        "charge_per_one_way": levers.charge_per_one_way,
        "car_banned": levers.car_banned_in_cbd,
    }


def build_economic_spillover(
    policy: PolicyDSL,
    *,
    shocks: Optional[Shocks] = None,
    horizon_months: Optional[float] = None,
    econ: EconParams = DEFAULT_ECON_PARAMS,
) -> EconomicSpilloverReport:
    """Assemble the economic spillover report for a compiled policy (SPEC §7.4)."""
    params, trend = apply_shocks(shocks)

    # Resolve the horizon against the real checkpoint grid (default 5 years).
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=params, reinvestment=True)
    b_behav = compute_world_b(policy, params=params, reinvestment=False)
    b_ts = build_world_b_timeline(
        policy, baseline=base, world_b_full=b_full,
        world_b_behaviour=b_behav, params=params, trend=trend,
    )
    delta = build_delta(base_ts, b_ts)
    target = 60.0 if horizon_months is None else horizon_months
    any_pts = delta.series[0].points
    hp = min(any_pts, key=lambda p: abs(p.t_months - target))
    horizon = Checkpoint(
        label=f"{hp.t_months:g}m", t_months=hp.t_months,
        t_years=round(hp.t_months / 12.0, 3),
    )
    t_years = horizon.t_years
    decay = _horizon_decay(t_years)

    flows = _steady_state_flows(policy, params)
    R = flows["annual_charge_revenue"]  # commuter cordon revenue (Simulated)
    vot = econ.value_of_time_per_min(params.money_to_minutes)
    vlo, vhi = econ.value_of_time_range_mult

    # Freight/delivery cordon revenue (Estimated — freight is not agent-modelled;
    # a documented share of baseline cordon entries, assumed volume-stable since
    # freight cannot easily switch mode). It is real public revenue, so it is
    # recycled alongside the commuter charge and its pass-through is a business cost.
    freight_rev = 0.0
    freight_daily_entries = 0.0
    if flows["charge_per_one_way"] > 0:
        freight_daily_entries = (
            flows["baseline_cbd_car_commuters"] * params.trips_per_commuter_per_day
            * econ.freight_entry_share
        )
        freight_rev = (
            freight_daily_entries * flows["charge_per_one_way"] * params.workdays_per_year
        )
    total_revenue = R + freight_rev

    channels: list[EconomicChannel] = []

    # ---- Channel 1 — charge transfer (household discretionary withdrawal) -----
    if R > 0:
        mpc = econ.local_consumption_mpc
        mlo, mhi = econ.local_consumption_mpc_range
        impact = -R * mpc
        channels.append(EconomicChannel(
            id="charge_transfer",
            name="Cordon charge withdrawn from household spending",
            mechanism="Charge revenue is money moved out of charged commuters' "
            "discretionary budgets; the locally-spent fraction leaves local demand "
            "until it is recycled (see revenue recycling).",
            direction="negative",
            physical_basis="annual cordon charge revenue (Simulated)",
            physical_value=round(R, 2),
            annual_impact=round(impact, 2),
            annual_impact_low=round(-R * mhi, 2),
            annual_impact_high=round(-R * mlo, 2),
            confidence=round(0.7 * decay, 3),
            confidence_label=_conf_label(0.7 * decay),
            assumptions=["local_consumption_mpc", "charge revenue (Simulated)"],
            note="A transfer, not a deadweight loss — recycled by the next channel.",
        ))

    # ---- Channel 2 — revenue recycling / fiscal multiplier --------------------
    # Recycles the full collected cordon revenue (commuter Simulated + freight
    # Estimated) so the freight cost channel below is balanced by its own revenue.
    if total_revenue > 0:
        m = econ.fiscal_multiplier
        flo, fhi = econ.fiscal_multiplier_range
        recycled_local = total_revenue * econ.revenue_local_share
        impact2 = recycled_local * m
        fbasis = (
            "annual cordon charge revenue (commuter Simulated + freight Estimated)"
            if freight_rev > 0 else "annual cordon charge revenue (Simulated)"
        )
        channels.append(EconomicChannel(
            id="revenue_recycling",
            name="Recycled revenue re-spent locally (transit + fund)",
            mechanism="All revenue collected at the cordon and allocated to public "
            "transport and the general fund is re-spent — labour-intensive transit "
            "operations and capital — circulating through the local economy at a "
            "fiscal multiplier.",
            direction="positive",
            physical_basis=fbasis,
            physical_value=round(total_revenue, 2),
            annual_impact=round(impact2, 2),
            annual_impact_low=round(recycled_local * flo, 2),
            annual_impact_high=round(recycled_local * fhi, 2),
            confidence=round(0.6 * decay, 3),
            confidence_label=_conf_label(0.6 * decay),
            assumptions=["fiscal_multiplier", "revenue_local_share",
                         "charge revenue (Simulated + freight Estimated)"],
            note="Net of the withdrawal and freight channels, reinvestment typically "
            "makes the charge locally positive.",
        ))

    # ---- Channel 3 — CBD retail footfall (avoidance − pedestrian amenity) ------
    deterred = max(0.0, flows["deterred_cbd_car_commuters"])
    avoid_frac = econ.cbd_trip_avoidance_fraction
    alo, ahi = econ.cbd_trip_avoidance_fraction_range
    spend = econ.cbd_retail_spend_per_commuter_year
    avoidance_loss = -deterred * avoid_frac * spend
    amenity = 0.0
    if flows["car_banned"]:
        up = econ.pedestrianisation_retail_uplift
        amenity = flows["cbd_commuters"] * spend * up
    foot_central = avoidance_loss + amenity
    foot_low = (
        -deterred * ahi * spend
        + (flows["cbd_commuters"] * spend * econ.pedestrianisation_retail_uplift_range[0]
           if flows["car_banned"] else 0.0)
    )
    foot_high = (
        -deterred * alo * spend
        + (flows["cbd_commuters"] * spend * econ.pedestrianisation_retail_uplift_range[1]
           if flows["car_banned"] else 0.0)
    )
    if deterred > 0 or flows["car_banned"]:
        channels.append(EconomicChannel(
            id="cbd_footfall",
            name="CBD retail & hospitality footfall",
            mechanism="Commuting is conserved (mode shift, not trip loss), so worker "
            "footfall holds; a small share of deterred car trips is foregone entirely, "
            "while pedestrianisation raises retail amenity and dwell-time spend.",
            direction="ambiguous",
            physical_basis="Δ CBD-bound car commuters (Simulated); shopper demand not "
            "agent-modelled",
            physical_value=round(deterred, 1),
            annual_impact=round(foot_central, 2),
            annual_impact_low=round(min(foot_low, foot_high), 2),
            annual_impact_high=round(max(foot_low, foot_high), 2),
            confidence=round(0.4 * decay, 3),
            confidence_label=_conf_label(0.4 * decay),
            assumptions=["cbd_trip_avoidance_fraction", "cbd_retail_spend_per_commuter_year",
                         "pedestrianisation_retail_uplift"],
            note="Sign is genuinely uncertain: pedestrianisation tends positive, a pure "
            "charge slightly negative. Discretionary shopper response is NOT modelled.",
        ))

    # ---- Channel 4 — business logistics / freight cost pass-through -----------
    if freight_rev > 0:
        freight_cost = freight_rev * econ.freight_cost_pass_through
        flo_s, fhi_s = econ.freight_entry_share_range
        base_entries = (flows["baseline_cbd_car_commuters"]
                        * params.trips_per_commuter_per_day)
        channels.append(EconomicChannel(
            id="business_logistics",
            name="Freight & delivery charge passed to CBD business",
            mechanism="Delivery/freight vehicles entering the cordon pay the charge; "
            "most of that cost is passed through to central businesses and their "
            "customers.",
            direction="negative",
            physical_basis="baseline CBD vehicle entries × freight share (Estimated — "
            "freight not in the synthetic population)",
            physical_value=round(freight_daily_entries, 1),
            annual_impact=round(-freight_cost, 2),
            annual_impact_low=round(
                -base_entries * fhi_s * flows["charge_per_one_way"]
                * params.workdays_per_year * econ.freight_cost_pass_through, 2),
            annual_impact_high=round(
                -base_entries * flo_s * flows["charge_per_one_way"]
                * params.workdays_per_year * econ.freight_cost_pass_through, 2),
            confidence=round(0.3 * decay, 3),
            confidence_label=_conf_label(0.3 * decay),
            assumptions=["freight_entry_share", "freight_cost_pass_through",
                         "charge_per_one_way (Simulated)"],
            note="Low confidence: freight demand is a documented ratio, not agent-modelled.",
        ))

    # ---- Channel 5 — commuter mode-switch travel-cost (value of time) ---------
    dmin = flows["delta_commuter_minutes_year"]
    if abs(dmin) > 1e-6:
        impact5 = -dmin * vot  # +Δminutes = more time spent = a cost (negative)
        channels.append(EconomicChannel(
            id="commuter_travel_cost",
            name="Commuter mode-switch travel-time cost",
            mechanism="Commuters who switch mode to avoid the charge/ban spend more (or "
            "less) time travelling; that time is valued at the model's value of time.",
            direction="negative" if dmin > 0 else "positive",
            physical_basis="Σ Δ commuter travel-minutes/year from mode switches (Simulated)",
            physical_value=round(dmin, 0),
            annual_impact=round(impact5, 2),
            annual_impact_low=round(-dmin * vot * (vhi if dmin > 0 else vlo), 2),
            annual_impact_high=round(-dmin * vot * (vlo if dmin > 0 else vhi), 2),
            confidence=round(0.5 * decay, 3),
            confidence_label=_conf_label(0.5 * decay),
            assumptions=["value_of_time_per_min = 1/money_to_minutes",
                         "mode switches (Simulated)"],
            note=f"Value of time ≈ {vot:.3f}/min, the inverse of the GC model's "
            "money↔time conversion (consistent with the mode-choice model). Excludes "
            "the charge money itself (counted in the transfer channel).",
        ))

    # ---- Net partial-equilibrium estimate -------------------------------------
    net = sum(c.annual_impact for c in channels)
    net_low = sum(c.annual_impact_low for c in channels)
    net_high = sum(c.annual_impact_high for c in channels)
    net_conf = round(min([c.confidence for c in channels], default=0.5), 3)

    sectors = _sector_exposure(channels, flows, policy)

    not_modelled = [
        "Congestion-relief time savings for remaining traffic — link speeds are fixed "
        "in this MVP; would require the spatial traffic-assignment layer (SPEC §7.7).",
        "Agglomeration, land-value and rent effects of improved central accessibility.",
        "Firm relocation / business entry-exit dynamics.",
        "Discretionary (non-commuter) shopper and tourist demand response.",
        "Wage / labour-market general equilibrium (this is partial-equilibrium only).",
        "Crowding-out / opportunity cost of the fiscal multiplier — recycled revenue "
        "is credited at a local multiplier without netting the alternative use of that "
        "money, so the net sign is sensitive to the multiplier assumption (Estimated).",
    ]

    if net > 0:
        dir_word = "net positive"
    elif net < 0:
        dir_word = "net negative"
    else:
        dir_word = "roughly neutral"
    headline = (
        f"Estimated {dir_word} local economic effect of ~{net:,.0f} "
        f"[{net_low:,.0f} … {net_high:,.0f}] local-currency/year at {horizon.label} "
        f"across {len(channels)} channel(s). Partial-equilibrium Estimated figure "
        f"built on Simulated mode-shift/revenue drivers — not a GDP number (SPEC §7.4/§34)."
    )

    return EconomicSpilloverReport(
        policy_id=policy.id,
        horizon=horizon,
        channels=channels,
        sector_exposure=sectors,
        net_annual_impact=round(net, 2),
        net_annual_impact_low=round(net_low, 2),
        net_annual_impact_high=round(net_high, 2),
        net_confidence=net_conf,
        not_modelled=not_modelled,
        assumptions={
            **econ.as_dict(),
            "value_of_time_per_min": round(vot, 4),
            "horizon_months": horizon.t_months,
        },
        headline=headline,
    )


def _sector_exposure(
    channels: list[EconomicChannel], flows: dict, policy: PolicyDSL
) -> list[SectorExposure]:
    """Roll the channels up into per-sector exposure records."""
    by_id = {c.id: c for c in channels}
    sectors: list[SectorExposure] = []

    foot = by_id.get("cbd_footfall")
    if foot is not None:
        sectors.append(SectorExposure(
            sector="retail_hospitality",
            direction="ambiguous",
            magnitude="moderate",
            mechanism="Footfall held by conserved commuting; pedestrian amenity up, "
            "car-avoidance down.",
            annual_impact_estimate=foot.annual_impact,
        ))
    if "revenue_recycling" in by_id:
        pt = float(policy.revenue_allocation.public_transport or 0.0)
        sectors.append(SectorExposure(
            sector="transit_operations",
            direction="positive",
            magnitude="high" if pt >= 0.5 else "moderate",
            mechanism="Reinvested revenue funds service operations and staffing.",
            annual_impact_estimate=round(by_id["revenue_recycling"].annual_impact * pt, 2),
        ))
        sectors.append(SectorExposure(
            sector="construction",
            direction="positive",
            magnitude="low",
            mechanism="Capital share of transit reinvestment supports short-run "
            "construction activity.",
            annual_impact_estimate=None,
        ))
    if "business_logistics" in by_id:
        sectors.append(SectorExposure(
            sector="logistics_freight",
            direction="negative",
            magnitude="low",
            mechanism="Cordon charge raises delivery costs into the centre.",
            annual_impact_estimate=by_id["business_logistics"].annual_impact,
        ))
    ct = by_id.get("commuter_travel_cost")
    sectors.append(SectorExposure(
        sector="households_labour",
        direction="negative" if (ct and ct.annual_impact < 0) else "ambiguous",
        magnitude="moderate",
        mechanism="Commuters bear mode-switch travel-time costs and the charge, partly "
        "offset by faster/cheaper transit from reinvestment.",
        annual_impact_estimate=(ct.annual_impact if ct else None),
    ))
    return sectors
