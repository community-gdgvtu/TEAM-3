"""Per-firm Business View service (SPEC §17 Business View).

The micro counterpart to the Citizen View: *click a firm* and see how the policy
changes its footfall, labour accessibility, deliveries, costs and revenue proxy —
plus the adaptation decisions its exposure implies — across the Time Machine.

Design (all deterministic, LLM-free — SPEC §34):

* **Same models as the aggregates.** A firm's **labour accessibility** is the
  commute generalized cost of *its own workers* — the synthetic commuters whose
  ``work_zone`` is the firm's zone — computed with the identical
  :func:`mode_options` / :func:`policy_mode_options` primitives ``/simulate`` and
  the Citizen View use. Its **footfall / deliveries / costs / revenue** reuse the
  *same economic coefficients* as ``/economy`` (:mod:`app.economy.params`:
  spend-per-visit, freight pass-through, car-avoidance fraction, pedestrianisation
  uplift) plus a few strictly firm-level allocation ratios
  (:mod:`app.business.params`). So the firm view can never disagree with the
  ``/economy`` and ``/simulate`` numbers beside it.

* **Firms come from the building stock.** Each commercial building in
  ``data/city/buildings.geojson`` is a firm; its jobs are allocated from its
  zone's total by floor-space share. Residential / park buildings are not firms.

* **Staged over the Time Machine.** Each metric is interpolated between three
  structural anchors — World A, behaviour-only World B (charge in force, transit
  uplift not yet built), fully-adapted World B — on the *same* behaviour /
  transit-ramp curves as the aggregate timeline (:mod:`app.simulation.timeline`),
  so the firm's picture (e.g. labour access dipping then recovering as the
  reinvested transit uplift lands) matches the dashboard's Time Machine.

* **Honest about the future (SPEC §9/§34).** Footfall / cost / revenue bands
  widen monotonically with the horizon via the same ``_band_rel`` the aggregate
  uses. Physical drivers are Simulated; the firm translation is Estimated.
"""

from __future__ import annotations

from dataclasses import replace as dc_replace

from .. import dataset
from ..baseline.model import CAR, mode_options, pick_mode
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.timeseries import _CHECKPOINTS
from ..economy.params import DEFAULT_ECON_PARAMS, EconParams
from ..policy.dsl import PolicyDSL
from ..simulation.levers import DEFAULT_SIM_PARAMS, PolicyLevers, SimParams, derive_levers
from ..simulation.model import policy_mode_options
from ..simulation.timeline import (
    DEFAULT_ADAPTATION,
    AdaptationParams,
    _band_rel,
    _behaviour_fraction,
    _transit_fraction,
)
from .params import (
    BUILDING_KIND_TO_SECTOR,
    DEFAULT_BUSINESS_PARAMS,
    BusinessParams,
)
from .schema import (
    BusinessView,
    FirmProfile,
    FirmSample,
    FirmSnapshot,
)

# Approx metres per degree at the synthetic city's latitude (~45°N). Only affects
# the *relative* floor-area allocation across firms, so this is a weak constant.
_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LON = 78_710.0  # 111_320 * cos(45°)


class FirmNotFound(LookupError):
    """Raised when a requested firm_id is not in the synthetic building stock."""


def _round(x: float, d: int = 2) -> float:
    return round(float(x), d)


def _behav_levers(policy: PolicyDSL, params: BaselineParams, sim: SimParams) -> PolicyLevers:
    """Reinvestment-off levers — the short-run anchor (mirrors compute_world_b)."""
    levers = derive_levers(policy, params=params, sim=sim)
    behav = dc_replace(levers, transit_fare_multiplier=1.0, transit_speed_multiplier=1.0)
    behav.rules = [r for r in levers.rules if r.name != "transit_reinvestment"]
    return behav


# --------------------------------------------------------------------------- #
# Firm stock (buildings → firms)
# --------------------------------------------------------------------------- #


def _footprint_sqm(geometry: dict) -> float:
    """Planar shoelace area of a polygon in lon/lat, converted to m²."""
    coords = geometry.get("coordinates") or []
    if not coords:
        return 0.0
    ring = coords[0]
    area2 = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area2 += x1 * y2 - x2 * y1
    deg_area = abs(area2) / 2.0
    return deg_area * _M_PER_DEG_LAT * _M_PER_DEG_LON


def _firm_stock(
    bp: BusinessParams = DEFAULT_BUSINESS_PARAMS,
) -> list[dict]:
    """The list of firms (commercial buildings) with allocated jobs + floor area.

    Jobs from ``zones.geojson`` are allocated to the commercial buildings in each
    zone by their gross-floor-area share (residential/park buildings excluded).
    Deterministic and policy-independent — describes the synthetic city only.
    """
    buildings = dataset.load_buildings()["features"]
    zi = dataset.zone_index()
    cbd = dataset.cbd_zone_ids()

    firms: list[dict] = []
    zone_floor: dict[str, float] = {}
    for idx, f in enumerate(buildings):
        p = f["properties"]
        sector = BUILDING_KIND_TO_SECTOR.get(p.get("k"))
        if sector is None:
            continue  # residential / park — not a firm
        zone = p["z"]
        height = float(p.get("h", bp.storey_height_m))
        floors = max(1, round(height / bp.storey_height_m))
        footprint = _footprint_sqm(f.get("geometry", {}))
        floor_area = footprint * floors
        zone_floor[zone] = zone_floor.get(zone, 0.0) + floor_area
        firms.append({
            "firm_id": f"FIRM-{idx:04d}",
            "index": idx,
            "sector": sector,
            "building_kind": p.get("k"),
            "zone_id": zone,
            "in_cbd": zone in cbd,
            "floors": floors,
            "floor_area_sqm": floor_area,
        })

    for firm in firms:
        zone = firm["zone_id"]
        zone_jobs = float(zi.get(zone, {}).get("jobs", 0.0))
        total_floor = zone_floor.get(zone, 0.0)
        share = firm["floor_area_sqm"] / total_floor if total_floor > 0 else 0.0
        firm["estimated_jobs"] = int(round(zone_jobs * share))
    return firms


# --------------------------------------------------------------------------- #
# Per-work-zone commuter aggregates (labour access + car deterrence)
# --------------------------------------------------------------------------- #


def _agent_gc(options: dict[str, float]) -> float:
    """Realized generalized cost = the chosen (minimum-cost) option."""
    return min(options.values())


def _zone_commuter_aggregates(
    levers_full: PolicyLevers,
    levers_behav: PolicyLevers,
    cbd: set[str],
    params: BaselineParams,
) -> dict[str, dict]:
    """One population pass → per work-zone commute-cost + car-arrival aggregates.

    For every work zone: the mean commuter generalized cost at each of the three
    structural anchors (World A / behaviour-B / full-B), the commuter headcount,
    the count arriving by car into the CBD in World A vs World B, and how many pay
    the charge. Mirrors the primitives ``/simulate`` and the Citizen View use.
    """
    agents = dataset.population_agents()
    agg: dict[str, dict] = {}
    for a in agents:
        zone = a["work_zone"]
        z = agg.get(zone)
        if z is None:
            z = agg[zone] = {
                "n": 0, "gc_a": 0.0, "gc_behav": 0.0, "gc_full": 0.0,
                "car_a": 0, "car_b": 0, "charge_payers": 0,
            }
        base_opts = mode_options(a, params)
        behav_opts = policy_mode_options(a, levers_behav, cbd, params)
        full_opts = policy_mode_options(a, levers_full, cbd, params)
        base_mode = pick_mode(base_opts)
        pol_mode = pick_mode(full_opts)
        into_cbd = a["commutes_into_cbd"]

        z["n"] += 1
        z["gc_a"] += _agent_gc(base_opts)
        z["gc_behav"] += _agent_gc(behav_opts)
        z["gc_full"] += _agent_gc(full_opts)
        if base_mode == CAR and into_cbd:
            z["car_a"] += 1
        if pol_mode == CAR and into_cbd:
            z["car_b"] += 1
            if levers_full.charge_per_one_way > 0 and not levers_full.is_exempt(a, cbd):
                z["charge_payers"] += 1
    for z in agg.values():
        n = max(1, z["n"])
        z["mean_gc_a"] = z["gc_a"] / n
        z["mean_gc_behav"] = z["gc_behav"] / n
        z["mean_gc_full"] = z["gc_full"] / n
    return agg


# --------------------------------------------------------------------------- #
# Firm selection
# --------------------------------------------------------------------------- #

_SELECTORS = (
    "representative",
    "most_exposed",
    "biggest_footfall_loss",
    "pedestrian_winner",
    "largest",
)


def _firm_exposure_key(firm: dict, zagg: dict, levers: PolicyLevers) -> float:
    """A crude scalar exposure used only for selection ranking (not reported)."""
    z = zagg.get(firm["zone_id"], {})
    gc_a = z.get("mean_gc_a", 1.0) or 1.0
    gc_full = z.get("mean_gc_full", gc_a)
    labour_pressure = max(0.0, gc_full - gc_a) / gc_a
    car_a = z.get("car_a", 0) or 0
    car_b = z.get("car_b", 0)
    deter = (car_a - car_b) / car_a if car_a > 0 else 0.0
    charge = 1.0 if (firm["in_cbd"] and levers.charge_per_one_way > 0) else 0.0
    return labour_pressure + deter + 0.5 * charge


def _select_firm(
    firms: list[dict], selector: str, zagg: dict, levers: PolicyLevers
) -> tuple[int, str]:
    """Return (list-index, resolved_selector) for the firm to profile."""
    n = len(firms)
    if selector == "representative":
        # A central retail/commercial firm — the kind a cordon policy is about.
        pool = [
            k for k in range(n)
            if firms[k]["in_cbd"] and firms[k]["sector"] in (
                "retail & hospitality", "retail / commercial podium", "mixed-use commercial"
            )
        ]
        if pool:
            areas = sorted(firms[k]["floor_area_sqm"] for k in pool)
            med = areas[len(areas) // 2]
            best = min(pool, key=lambda k: (abs(firms[k]["floor_area_sqm"] - med), firms[k]["index"]))
            return best, "representative"
        selector = "largest"

    if selector == "largest":
        best = max(range(n), key=lambda k: (firms[k]["estimated_jobs"], -firms[k]["index"]))
        return best, "largest"

    if selector == "most_exposed":
        best = max(range(n), key=lambda k: (_firm_exposure_key(firms[k], zagg, levers), -firms[k]["index"]))
        return best, "most_exposed"

    if selector == "biggest_footfall_loss":
        # CBD firms losing the most car-borne customers.
        def loss(k: int) -> float:
            z = zagg.get(firms[k]["zone_id"], {})
            car_a = z.get("car_a", 0) or 0
            deter = (car_a - z.get("car_b", 0)) / car_a if car_a > 0 else 0.0
            return deter if firms[k]["in_cbd"] else 0.0
        best = max(range(n), key=lambda k: (loss(k), firms[k]["estimated_jobs"], -firms[k]["index"]))
        return best, "biggest_footfall_loss"

    # pedestrian_winner: a central retail firm under a car ban gains footfall.
    if levers.car_banned_in_cbd:
        pool = [k for k in range(n) if firms[k]["in_cbd"] and firms[k]["sector"] in (
            "retail & hospitality", "retail / commercial podium", "mixed-use commercial"
        )]
        if pool:
            best = max(pool, key=lambda k: (firms[k]["estimated_jobs"], -firms[k]["index"]))
            return best, "pedestrian_winner"
    # fall back to representative-style pick
    return _select_firm(firms, "largest", zagg, levers)


def _find_firm(firms: list[dict], firm_id: str) -> int:
    for k, f in enumerate(firms):
        if f["firm_id"] == firm_id:
            return k
    raise FirmNotFound(firm_id)


# --------------------------------------------------------------------------- #
# Build the view
# --------------------------------------------------------------------------- #


def build_business_view(
    policy: PolicyDSL,
    *,
    firm_id: str | None = None,
    selector: str = "representative",
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    econ: EconParams = DEFAULT_ECON_PARAMS,
    bp: BusinessParams = DEFAULT_BUSINESS_PARAMS,
    adaptation: AdaptationParams = DEFAULT_ADAPTATION,
) -> BusinessView:
    """Build the full Business View for one firm under ``policy`` (SPEC §17)."""
    cbd = dataset.cbd_zone_ids()
    levers_full = derive_levers(policy, params=params, sim=sim)
    levers_behav = _behav_levers(policy, params, sim)

    firms = _firm_stock(bp)
    zagg = _zone_commuter_aggregates(levers_full, levers_behav, cbd, params)

    if firm_id is not None:
        idx = _find_firm(firms, firm_id)
        resolved_selector = f"firm_id:{firm_id}"
    else:
        if selector not in _SELECTORS:
            selector = "representative"
        idx, resolved_selector = _select_firm(firms, selector, zagg, levers_full)

    firm = firms[idx]
    zone = firm["zone_id"]
    z = zagg.get(zone, {"mean_gc_a": 1.0, "mean_gc_behav": 1.0, "mean_gc_full": 1.0,
                        "car_a": 0, "car_b": 0, "charge_payers": 0, "n": 0})
    jobs = firm["estimated_jobs"]
    sector = firm["sector"]

    # --- Labour accessibility anchors (index 100 = baseline ease) -----------
    gc_a = z["mean_gc_a"] or 1.0
    acc_a = 100.0
    acc_behav = 100.0 * gc_a / (z["mean_gc_behav"] or gc_a)
    acc_full = 100.0 * gc_a / (z["mean_gc_full"] or gc_a)

    # --- Footfall anchors ---------------------------------------------------
    worker_footfall = float(jobs)  # conserved (mode shift, not job loss)
    cust_mult = bp.customer_multiplier(sector)
    customer_base = jobs * cust_mult
    car_share = bp.customer_car_share_cbd if firm["in_cbd"] else bp.customer_car_share_outer
    car_a, car_b = z.get("car_a", 0), z.get("car_b", 0)
    frac_car_deterred = (car_a - car_b) / car_a if car_a > 0 else 0.0
    # Lost customers: deterred car-borne customers who forgo the trip entirely.
    lost_customers = customer_base * car_share * frac_car_deterred * econ.cbd_trip_avoidance_fraction
    amenity_customers = (
        customer_base * econ.pedestrianisation_retail_uplift if levers_full.car_banned_in_cbd else 0.0
    )
    cust_a = customer_base
    cust_policy = max(0.0, customer_base - lost_customers + amenity_customers)  # behav & full anchor

    foot_a = worker_footfall + cust_a
    foot_behav = worker_footfall + cust_policy
    foot_full = foot_behav  # transit uplift doesn't materially move footfall

    # --- Deliveries + cost anchors ------------------------------------------
    deliveries_daily = (firm["floor_area_sqm"] / 1000.0) * bp.deliveries_rate(sector)
    charge = levers_full.charge_per_one_way
    # A firm inside the cordon pays the charge on each inbound delivery.
    if firm["in_cbd"] and charge > 0:
        delivery_cost_annual = (
            deliveries_daily * charge * params.workdays_per_year * bp.delivery_cost_pass_through
        )
    else:
        delivery_cost_annual = 0.0
    cost_a = 0.0
    cost_behav = delivery_cost_annual  # charge in force at both policy anchors
    cost_full = delivery_cost_annual

    # --- Revenue proxy anchors (footfall × spend) ---------------------------
    spend = bp.spend_per_customer_visit
    slo, shi = bp.spend_per_customer_visit_range
    rev_a = cust_a * spend * params.workdays_per_year
    rev_policy = cust_policy * spend * params.workdays_per_year

    # Fixed per-quantity scales for monotone-widening bands (SPEC §9/§34).
    foot_scale = max(abs(foot_a), abs(foot_behav), 1.0)
    cost_scale = max(abs(cost_a), abs(cost_behav), 1.0)
    rev_scale = max(abs(rev_a), abs(rev_policy), 1.0)

    def _snapshot(label: str, months: float) -> FirmSnapshot:
        fb = _behaviour_fraction(months, adaptation)
        ft = _transit_fraction(months, adaptation)
        years = months / 12.0
        rel = _band_rel(years, adaptation)

        footfall = foot_a + fb * (foot_behav - foot_a) + ft * (foot_full - foot_behav)
        acc = acc_a + fb * (acc_behav - acc_a) + ft * (acc_full - acc_behav)
        cost = cost_a + fb * (cost_behav - cost_a) + ft * (cost_full - cost_behav)
        revenue = rev_a + fb * (rev_policy - rev_a) + ft * (rev_policy - rev_policy)

        # Revenue-band edges follow the spend-per-visit uncertainty, scaled to
        # the staged customer footfall (revenue is the least certain proxy).
        cust_now = footfall - worker_footfall
        rev_lo = cust_now * slo * params.workdays_per_year
        rev_hi = cust_now * shi * params.workdays_per_year

        net_change = (revenue - cost) - rev_a
        net_pct = 100.0 * net_change / rev_a if rev_a > 0 else 0.0

        foot_half = foot_scale * rel * 0.15
        cost_half = cost_scale * rel * 0.3
        rev_half = rev_scale * rel * 0.2
        return FirmSnapshot(
            label=label,
            t_months=round(months, 3),
            daily_footfall=_round(footfall, 1),
            daily_footfall_low=_round(max(0.0, footfall - foot_half), 1),
            daily_footfall_high=_round(footfall + foot_half, 1),
            labour_accessibility_index=_round(acc, 1),
            daily_deliveries=_round(deliveries_daily, 2),
            annual_cost_added=_round(cost, 2),
            annual_cost_added_low=_round(max(0.0, cost - cost_half), 2),
            annual_cost_added_high=_round(cost + cost_half, 2),
            revenue_proxy_annual=_round(revenue, 2),
            revenue_proxy_annual_low=_round(min(rev_lo, rev_hi) - rev_half, 2),
            revenue_proxy_annual_high=_round(max(rev_lo, rev_hi) + rev_half, 2),
            net_revenue_proxy_change_pct=_round(net_pct, 2),
        )

    trajectory = [_snapshot(label, months) for label, months in _CHECKPOINTS]
    before = _snapshot("BEFORE POLICY", 0.0)

    profile = FirmProfile(
        firm_id=firm["firm_id"],
        sector=sector,
        building_kind=str(firm["building_kind"]),
        zone_id=zone,
        in_central_district=firm["in_cbd"],
        floors=int(firm["floors"]),
        floor_area_sqm=_round(firm["floor_area_sqm"], 1),
        estimated_jobs=int(jobs),
    )

    end = trajectory[-1]
    headline = (
        f"{profile.firm_id} ({sector}, {zone}"
        f"{', central' if firm['in_cbd'] else ''}): footfall "
        f"{before.daily_footfall:g}→{end.daily_footfall:g}/day, labour access "
        f"{before.labour_accessibility_index:g}→{end.labour_accessibility_index:g}, "
        f"added cost ${end.annual_cost_added:,.0f}/yr, net revenue proxy "
        f"{end.net_revenue_proxy_change_pct:+.1f}%."
    )

    adaptation_decisions = _adaptation_decisions(
        firm, z, levers_full, delivery_cost_annual, acc_full, end, adaptation, bp
    )
    explanation = _build_explanation(
        firm, z, levers_full, delivery_cost_annual, frac_car_deterred,
        acc_behav, acc_full, trajectory, adaptation,
    )

    return BusinessView(
        policy_id=policy.id,
        selector=resolved_selector,
        profile=profile,
        before_policy=before,
        trajectory=trajectory,
        adaptation_decisions=adaptation_decisions,
        headline=headline,
        explanation=explanation,
        not_modelled=[
            "Jobs, floor area and delivery counts are allocated from zone totals by "
            "floor-space share, not measured per firm; customers/deliveries are not "
            "agent-modelled (SPEC §6) — the revenue figure is an Estimated proxy, "
            "meaningful only as a before/after ratio, never as an absolute turnover.",
            "Footfall change captures deterred car-borne customers and pedestrianisation "
            "amenity only; wider retail catchment, tourism, online substitution and "
            "business entry/exit are not modelled.",
            "Labour accessibility is the commute generalized cost of the firm's own "
            "workers (same mode-choice model as /simulate); it does not model wage "
            "adjustment, hiring-radius change or labour-market equilibrium.",
            "Adaptation decisions are deterministic rules implied by the firm's exposure, "
            "not an optimised or behavioural firm-response simulation.",
        ],
        params={
            **bp.as_dict(),
            "cbd_trip_avoidance_fraction": econ.cbd_trip_avoidance_fraction,
            "pedestrianisation_retail_uplift": econ.pedestrianisation_retail_uplift,
            "workdays_per_year": params.workdays_per_year,
            "transit_lag_months": adaptation.transit_lag_months,
            "note": (
                "labour accessibility uses the same mode-choice model as /simulate; "
                "footfall/deliveries/cost/revenue reuse the /economy coefficients; all "
                "staged on the same adaptation curve as the aggregate Time Machine."
            ),
        },
    )


def _adaptation_decisions(
    firm: dict,
    z: dict,
    levers: PolicyLevers,
    delivery_cost_annual: float,
    acc_full: float,
    end: FirmSnapshot,
    adaptation: AdaptationParams,
    bp: BusinessParams,
) -> list[str]:
    """Deterministic firm adaptation responses implied by exposure (SPEC §17)."""
    out: list[str] = []
    retail = firm["sector"] in (
        "retail & hospitality", "retail / commercial podium", "mixed-use commercial"
    )

    if delivery_cost_annual > 0:
        out.append(
            f"Absorb or pass through the delivery-charge cost (~${delivery_cost_annual:,.0f}/yr): "
            "consolidate inbound deliveries into fewer, off-peak trips to cut charged entries."
        )
    if levers.car_banned_in_cbd and retail:
        out.append(
            "Lean into higher pedestrian footfall from the car-free centre — extend "
            "frontage, outdoor seating and pedestrian-facing hours; arrange kerbside "
            "loading windows for the restricted vehicle access."
        )
    if acc_full < 95.0:
        out.append(
            "Labour-access pressure: support staff with transit passes or staggered "
            f"hours until the reinvested transit uplift phases in (~month "
            f"{adaptation.transit_lag_months:g})."
        )
    if end.net_revenue_proxy_change_pct < -100.0 * bp.relocation_risk_revenue_drop:
        out.append(
            f"Relocation / downsizing risk flag: modelled net revenue proxy falls "
            f"{end.net_revenue_proxy_change_pct:.1f}% — monitor footfall and review "
            "the central location if the trend persists."
        )
    if not firm["in_cbd"] and levers.charge_per_one_way > 0 and not levers.car_banned_in_cbd:
        out.append(
            "Outside the priced cordon — minimal direct exposure; may gain relative "
            "footfall as central car access tightens."
        )
    if not out:
        out.append(
            "No adaptation required — this firm's footfall, deliveries and labour access "
            "are essentially unchanged by the policy."
        )
    return out


def _build_explanation(
    firm: dict,
    z: dict,
    levers: PolicyLevers,
    delivery_cost_annual: float,
    frac_car_deterred: float,
    acc_behav: float,
    acc_full: float,
    trajectory: list[FirmSnapshot],
    adaptation: AdaptationParams,
) -> list[str]:
    """Deterministic 'Why?' narrative tied to the staged model (SPEC §17)."""
    lines: list[str] = []
    start, end = trajectory[0], trajectory[-1]
    retail = firm["sector"] in (
        "retail & hospitality", "retail / commercial podium", "mixed-use commercial"
    )

    changed = (
        abs(end.daily_footfall - start.daily_footfall) > 0.5
        or abs(end.labour_accessibility_index - 100.0) > 0.5
        or delivery_cost_annual > 0
    )
    if not changed:
        lines.append(
            "This policy barely touches this firm: it sits outside the priced area (or "
            "the charge does not affect its customers, workers or deliveries), so its "
            "footfall, labour access and costs are essentially unchanged."
        )
        return lines

    if delivery_cost_annual > 0:
        lines.append(
            f"The firm is inside the cordon, so its inbound deliveries pay the charge — "
            f"about ${delivery_cost_annual:,.0f}/year in pass-through cost."
        )
    if firm["in_cbd"] and frac_car_deterred > 0 and retail:
        lines.append(
            f"Roughly {frac_car_deterred*100:.0f}% of car arrivals into the district are "
            "deterred by the charge; a small share of car-borne customers forgo the trip, "
            f"trimming footfall from {start.daily_footfall:g} toward {trajectory[1].daily_footfall:g}/day."
        )
    if levers.car_banned_in_cbd and retail:
        lines.append(
            "With cars removed from the centre, pedestrian footfall and dwell-time rise, "
            "partly offsetting lost car-borne trade for a street-facing firm."
        )
    if acc_full < acc_behav - 0.3:
        lines.append("Labour accessibility keeps improving as the reinvested transit uplift lands.")
    if acc_full < 99.5 or acc_behav < 99.5:
        peak_low = min(trajectory, key=lambda s: s.labour_accessibility_index)
        lines.append(
            f"Labour accessibility for its workers dips to about "
            f"{peak_low.labour_accessibility_index:g} (higher commute cost) around "
            f"{peak_low.label}, then recovers toward {end.labour_accessibility_index:g} as the "
            f"revenue-funded transit service phases in from ~month {adaptation.transit_lag_months:g}."
        )
    lines.append(
        f"Net, the firm's modelled revenue proxy ends {end.net_revenue_proxy_change_pct:+.1f}% vs "
        "baseline after added costs — an Estimated proxy, not a turnover forecast."
    )
    return lines


# --------------------------------------------------------------------------- #
# Sample picker (policy-independent)
# --------------------------------------------------------------------------- #


def sample_firms(limit: int = 6, bp: BusinessParams = DEFAULT_BUSINESS_PARAMS) -> list[FirmSample]:
    """A small, diverse, deterministic set of firms for a UI picker (SPEC §17).

    Policy-independent — describes the synthetic building stock only. Picks the
    largest-jobs firm in each distinct sector, preferring central firms, so the
    picker spans sectors and the central/outer split.
    """
    firms = _firm_stock(bp)
    by_sector: dict[str, dict] = {}
    for firm in firms:
        sec = firm["sector"]
        cur = by_sector.get(sec)
        # prefer central firms, then more jobs, then lowest index (deterministic)
        key = (firm["in_cbd"], firm["estimated_jobs"], -firm["index"])
        if cur is None or key > (cur["in_cbd"], cur["estimated_jobs"], -cur["index"]):
            by_sector[sec] = firm

    picked = sorted(by_sector.values(), key=lambda f: (-f["estimated_jobs"], f["index"]))
    out: list[FirmSample] = []
    for firm in picked[:limit]:
        out.append(FirmSample(
            firm_id=firm["firm_id"],
            label=f"{firm['sector']}, {firm['zone_id']}"
                  f"{' (central)' if firm['in_cbd'] else ''}, ~{firm['estimated_jobs']} jobs",
            sector=firm["sector"],
            zone_id=firm["zone_id"],
            in_central_district=firm["in_cbd"],
            estimated_jobs=int(firm["estimated_jobs"]),
        ))
    return out
