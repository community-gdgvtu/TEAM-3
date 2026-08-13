"""Per-agent Citizen View service (SPEC §17 Citizen View, §31 Agent State).

Design (all deterministic, LLM-free — SPEC §34):

* **Same models as the aggregates.** A household's World-A mode/cost comes from
  :func:`app.baseline.model.mode_options`; its World-B mode/cost from
  :func:`app.simulation.model.policy_mode_options` — the identical primitives
  ``/simulate`` and ``/microsim`` use. Its policy support comes from
  :func:`app.opinion.model._agent_support`, the identical per-agent function
  ``/public`` aggregates. So a citizen's numbers can never disagree with the
  dashboard beside them (a guarantee the tests pin).

* **Staged over the Time Machine.** A single World-B snapshot is the *fully
  adapted* end-state. The Citizen View interpolates the household between three
  structural anchors — World A, behaviour-only World B (charge in force, transit
  uplift not yet built) and fully-adapted World B — using the *same* behaviour /
  transit-ramp curves as the aggregate timeline
  (:mod:`app.simulation.timeline`). This is what reproduces the SPEC §17 story:
  a commute that worsens (bus capacity lags demand) then improves (revenue-funded
  service enters operation) before settling.

* **Honest about the future (SPEC §9/§34).** The per-horizon commute / cost band
  widens monotonically with the horizon, using the same ``_band_rel`` the
  aggregate uses.
"""

from __future__ import annotations

from dataclasses import replace as dc_replace

from .. import dataset
from ..baseline.model import CAR, TRANSIT, WALK, _one_way_minutes, mode_options, pick_mode
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.timeseries import _CHECKPOINTS
from ..microsim.model import _agent_impact
from ..opinion.model import _agent_support
from ..opinion.params import DEFAULT_OPINION_PARAMS, OpinionParams
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
from .schema import (
    AgentState,
    CitizenProfile,
    CitizenSample,
    CitizenSnapshot,
    CitizenView,
)


class CitizenNotFound(LookupError):
    """Raised when a requested agent_id is not in the synthetic population."""


def _round(x: float, d: int = 2) -> float:
    return round(float(x), d)


def _behav_levers(policy: PolicyDSL, params: BaselineParams, sim: SimParams) -> PolicyLevers:
    """Reinvestment-off levers — the short-run anchor (mirrors compute_world_b)."""
    levers = derive_levers(policy, params=params, sim=sim)
    # Behavioural substitution has happened, but the revenue-funded transit
    # capacity has not been built yet, so the service-quality levers are neutral.
    behav = dc_replace(levers, transit_fare_multiplier=1.0, transit_speed_multiplier=1.0)
    behav.rules = [r for r in levers.rules if r.name != "transit_reinvestment"]
    return behav


def _leg(agent: dict, mode: str, levers: PolicyLevers | None, cbd: set[str], params: BaselineParams):
    """One-way (minutes, money) for ``agent`` travelling by ``mode``.

    Mirrors the time / money decomposition inside :func:`mode_options` /
    :func:`policy_mode_options` exactly (``levers is None`` ⇒ World-A baseline).
    """
    dist = agent["commute_distance_km"]
    into_cbd = agent["commutes_into_cbd"]
    if mode == WALK:
        return _one_way_minutes(dist, params.walk_speed_kmh, 0.0), 0.0
    if mode == CAR:
        speed = params.car_speed_cbd_kmh if into_cbd else params.car_speed_kmh
        minutes = _one_way_minutes(dist, speed, params.car_overhead_min)
        money = dist * params.car_cost_per_km
        if (
            levers is not None
            and into_cbd
            and levers.charge_per_one_way > 0
            and not levers.is_exempt(agent, cbd)
        ):
            money += levers.charge_per_one_way
        return minutes, money
    # TRANSIT
    speed_mult = levers.transit_speed_multiplier if levers is not None else 1.0
    fare_mult = levers.transit_fare_multiplier if levers is not None else 1.0
    minutes = _one_way_minutes(dist, params.transit_speed_kmh * speed_mult, params.transit_overhead_min)
    money = params.transit_fare * fare_mult
    return minutes, money


def _charge_leg(agent: dict, mode: str, levers: PolicyLevers | None, cbd: set[str]) -> float:
    """Per-one-way cordon charge this agent actually pays in the given state."""
    if levers is None or mode != CAR:
        return 0.0
    if (
        agent["commutes_into_cbd"]
        and levers.charge_per_one_way > 0
        and not levers.is_exempt(agent, cbd)
    ):
        return levers.charge_per_one_way
    return 0.0


def _flags(agent: dict, base_mode: str, pol_mode: str, levers: PolicyLevers, cbd: set[str]):
    """Fairness flags for the opinion model (mirrors compute_public_opinion)."""
    into_cbd = agent["commutes_into_cbd"]
    would_pay = (
        into_cbd
        and levers.charge_per_one_way > 0
        and agent["car_access"]
        and not (into_cbd and levers.car_banned_in_cbd)
    )
    exempt = levers.is_exempt(agent, cbd)
    paid_charge = pol_mode == CAR and into_cbd and levers.charge_per_one_way > 0 and not exempt
    exempt_benefit = would_pay and exempt and pol_mode == CAR
    forced_off_car = (
        base_mode == CAR and into_cbd and levers.car_banned_in_cbd and pol_mode != CAR
    )
    return paid_charge, exempt_benefit, forced_off_car


def _stance(support: float) -> str:
    if support > 0.15:
        return "supports"
    if support < -0.15:
        return "opposes"
    return "neutral"


def _monthly(money_one_way: float, params: BaselineParams) -> float:
    """Convert a per-one-way money cost to a monthly transport cost."""
    workdays_per_month = params.workdays_per_year / 12.0
    return money_one_way * params.trips_per_commuter_per_day * workdays_per_month


# --------------------------------------------------------------------------- #
# Agent selection
# --------------------------------------------------------------------------- #

_SELECTORS = (
    "representative",
    "most_burdened",
    "biggest_loser",
    "biggest_winner",
    "median",
)


def _select_agent(
    agents: list[dict],
    selector: str,
    levers_full: PolicyLevers,
    cbd: set[str],
    params: BaselineParams,
    sim: SimParams,
) -> tuple[int, str]:
    """Return (index, resolved_selector) for the household to profile."""
    n = len(agents)
    if selector == "representative":
        # The SPEC §17 archetype: a CBD-commuting car driver near the median
        # income of that group — the household a congestion charge is *about*.
        pool = [
            k
            for k in range(n)
            if agents[k]["commutes_into_cbd"]
            and agents[k]["car_access"]
            and pick_mode(mode_options(agents[k], params)) == CAR
        ]
        if pool:
            incomes = sorted(float(agents[k].get("income", 0.0)) for k in pool)
            median_income = incomes[len(incomes) // 2]
            best = min(
                pool,
                key=lambda k: (abs(float(agents[k].get("income", 0.0)) - median_income), agents[k]["agent_id"]),
            )
            return best, "representative"
        selector = "median"  # fall back if no CBD car commuter exists

    impacts = [_agent_impact(a, levers_full, cbd, params, sim) for a in agents]

    if selector == "most_burdened":
        payers = [k for k in range(n) if impacts[k].charge_paid_daily > 0]
        if payers:
            best = max(payers, key=lambda k: (impacts[k].burden_pct, agents[k]["agent_id"]))
            return best, "most_burdened"
        selector = "biggest_loser"

    if selector == "biggest_loser":
        best = max(range(n), key=lambda k: (impacts[k].gc_change_min, agents[k]["agent_id"]))
        return best, "biggest_loser"

    if selector == "biggest_winner":
        best = min(range(n), key=lambda k: (impacts[k].gc_change_min, agents[k]["agent_id"]))
        return best, "biggest_winner"

    # median (default fallback): the agent at the median generalized-cost change.
    order = sorted(range(n), key=lambda k: (impacts[k].gc_change_min, agents[k]["agent_id"]))
    return order[len(order) // 2], "median"


def _find_agent(agents: list[dict], agent_id: str) -> int:
    for k, a in enumerate(agents):
        if a["agent_id"] == agent_id:
            return k
    raise CitizenNotFound(agent_id)


# --------------------------------------------------------------------------- #
# Build the view
# --------------------------------------------------------------------------- #


def build_citizen_view(
    policy: PolicyDSL,
    *,
    agent_id: str | None = None,
    selector: str = "representative",
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    op: OpinionParams = DEFAULT_OPINION_PARAMS,
    adaptation: AdaptationParams = DEFAULT_ADAPTATION,
) -> CitizenView:
    """Build the full Citizen View for one household under ``policy`` (SPEC §17/§31)."""
    agents = dataset.population_agents()
    cbd = dataset.cbd_zone_ids()
    levers_full = derive_levers(policy, params=params, sim=sim)
    levers_behav = _behav_levers(policy, params, sim)
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)

    if agent_id is not None:
        idx = _find_agent(agents, agent_id)
        resolved_selector = f"agent_id:{agent_id}"
    else:
        if selector not in _SELECTORS:
            selector = "representative"
        idx, resolved_selector = _select_agent(agents, selector, levers_full, cbd, params, sim)

    agent = agents[idx]

    # --- Three structural anchors for this household -----------------------
    base_opts = mode_options(agent, params)
    base_mode = pick_mode(base_opts)
    base_cost = base_opts[base_mode]
    min_a, money_a = _leg(agent, base_mode, None, cbd, params)

    behav_opts = policy_mode_options(agent, levers_behav, cbd, params)
    behav_mode = pick_mode(behav_opts)
    behav_cost = behav_opts[behav_mode]
    min_behav, money_behav = _leg(agent, behav_mode, levers_behav, cbd, params)
    charge_behav = _charge_leg(agent, behav_mode, levers_behav, cbd)

    full_opts = policy_mode_options(agent, levers_full, cbd, params)
    full_mode = pick_mode(full_opts)
    full_cost = full_opts[full_mode]
    min_full, money_full = _leg(agent, full_mode, levers_full, cbd, params)
    charge_full = _charge_leg(agent, full_mode, levers_full, cbd)

    # --- Support anchors (reusing the /public per-agent function) ----------
    # s_A: pre-policy — material 0, no fairness signal, just the ideological prior.
    _, _, s_a = _agent_support(
        agent, base_cost, base_cost, base_mode, False, False, False, levers_full, 0.0, op
    )
    pb, eb, fb_ = _flags(agent, base_mode, behav_mode, levers_behav, cbd)
    _, _, s_behav = _agent_support(
        agent, base_cost, behav_cost, behav_mode, pb, eb, fb_, levers_behav, pt_share, op
    )
    pf, ef, ff = _flags(agent, base_mode, full_mode, levers_full, cbd)
    _, _, s_full = _agent_support(
        agent, base_cost, full_cost, full_mode, pf, ef, ff, levers_full, pt_share, op
    )

    # Fixed per-quantity scales for a monotone-widening band (SPEC §9/§34).
    min_scale = max(abs(min_a), abs(min_behav), abs(min_full), 1.0)
    money_scale = max(abs(money_a), abs(money_behav), abs(money_full), 0.1)

    def _snapshot(label: str, months: float) -> CitizenSnapshot:
        fb = _behaviour_fraction(months, adaptation)
        ft = _transit_fraction(months, adaptation)
        years = months / 12.0

        minutes = min_a + fb * (min_behav - min_a) + ft * (min_full - min_behav)
        money = money_a + fb * (money_behav - money_a) + ft * (money_full - money_behav)
        charge = fb * charge_behav + ft * (charge_full - charge_behav)
        support = s_a + fb * (s_behav - s_a) + ft * (s_full - s_behav)

        # Discrete mode overlay: at T0 the household is in its baseline mode;
        # behavioural substitution moves them to the short-run mode; a later
        # transit-ramp mode switch (if any) lands once that ramp dominates.
        if fb <= 0.5:
            mode = base_mode
        elif full_mode != behav_mode and ft >= 0.5:
            mode = full_mode
        else:
            mode = behav_mode

        rel = _band_rel(years, adaptation)
        min_half = min_scale * rel
        money_half = money_scale * rel
        monthly = _monthly(money, params)
        monthly_low = _monthly(money - money_half, params)
        monthly_high = _monthly(money + money_half, params)

        return CitizenSnapshot(
            label=label,
            t_months=round(months, 3),
            mode=mode,
            commute_minutes_one_way=_round(minutes, 1),
            commute_minutes_low=_round(max(0.0, minutes - min_half), 1),
            commute_minutes_high=_round(minutes + min_half, 1),
            monthly_transport_cost=_round(monthly, 2),
            monthly_transport_cost_low=_round(max(0.0, monthly_low), 2),
            monthly_transport_cost_high=_round(monthly_high, 2),
            charge_paid_monthly=_round(_monthly(charge, params), 2),
            policy_support=_round(support, 3),
            stance=_stance(support),
        )

    trajectory = [_snapshot(label, months) for label, months in _CHECKPOINTS]
    before = _snapshot("BEFORE POLICY", 0.0)

    agent_states = [
        AgentState(
            agent_id=agent["agent_id"],
            t=snap.t_months,
            location=agent["home_zone"],
            income=_round(float(agent.get("income", 0.0)), 2),
            commute_minutes=snap.commute_minutes_one_way,
            monthly_transport_cost=snap.monthly_transport_cost,
            policy_support=snap.policy_support,
        )
        for snap in trajectory
    ]

    profile = CitizenProfile(
        agent_id=agent["agent_id"],
        age=int(agent["age"]),
        household_size=int(agent["household_size"]),
        income_monthly=_round(float(agent.get("income", 0.0)), 2),
        income_annual=_round(float(agent.get("income", 0.0)) * 12.0, 2),
        income_band=str(agent["income_band"]),
        occupation=str(agent["occupation"]),
        home_zone=str(agent["home_zone"]),
        home_in_central_district=agent["home_zone"] in cbd,
        work_zone=str(agent["work_zone"]),
        commutes_into_cbd=bool(agent["commutes_into_cbd"]),
        commute_distance_km=_round(float(agent["commute_distance_km"]), 3),
        car_access=bool(agent["car_access"]),
        public_transit_access=bool(agent["public_transit_access"]),
    )

    end = trajectory[-1]
    headline = (
        f"{profile.agent_id} ({profile.occupation}, {profile.income_band} income, "
        f"{profile.home_zone}{'→CBD' if profile.commutes_into_cbd else ''}): "
        f"commute {before.commute_minutes_one_way:g}→{end.commute_minutes_one_way:g} min, "
        f"transport ${before.monthly_transport_cost:g}→${end.monthly_transport_cost:g}/mo, "
        f"support {end.policy_support:+.2f} ({end.stance})."
    )

    explanation = _build_explanation(
        profile, base_mode, behav_mode, full_mode, charge_full, trajectory,
        pt_share, ef, ff, adaptation, params,
    )

    return CitizenView(
        policy_id=policy.id,
        selector=resolved_selector,
        profile=profile,
        before_policy=before,
        trajectory=trajectory,
        agent_states=agent_states,
        headline=headline,
        explanation=explanation,
        not_modelled=[
            "Only this household's commute welfare is modelled — not wider household "
            "budgets, non-commute trips, labour-supply changes or in-kind gains from "
            "reinvested revenue.",
            "The staged trajectory interpolates three structural anchors (World A, "
            "behaviour-only World B, fully-adapted World B) on the same adaptation "
            "curve as the aggregate timeline; it is not a month-by-month agent "
            "simulation of this individual.",
            "This is a synthetic micro-agent, not a real person; its attributes are "
            "seeded distributional draws (SPEC §6).",
            "Support uses the population opinion model's fairness signals; individual "
            "political affiliation is not modelled.",
        ],
        params={
            "money_to_minutes": params.money_to_minutes,
            "trips_per_commuter_per_day": params.trips_per_commuter_per_day,
            "workdays_per_year": params.workdays_per_year,
            "transit_lag_months": adaptation.transit_lag_months,
            "behaviour_tau_months": adaptation.behaviour_tau_months,
            "transit_tau_months": adaptation.transit_tau_months,
            "note": (
                "commute/cost/support interpolate three structural anchors using the "
                "same behaviour/transit-ramp curves as the aggregate Time Machine; "
                "the far-horizon support equals this agent's /public contribution."
            ),
        },
    )


def _build_explanation(
    profile: CitizenProfile,
    base_mode: str,
    behav_mode: str,
    full_mode: str,
    charge_full: float,
    trajectory: list[CitizenSnapshot],
    pt_share: float,
    exempt_benefit: bool,
    forced_off_car: bool,
    adaptation: AdaptationParams,
    params: BaselineParams,
) -> list[str]:
    """Deterministic 'Why?' narrative tied to the staged model (SPEC §17)."""
    lines: list[str] = []
    mode_name = {CAR: "drive", TRANSIT: "take public transit", WALK: "walk"}

    start, end = trajectory[0], trajectory[-1]
    commute_moves = abs(end.commute_minutes_one_way - start.commute_minutes_one_way) > 0.1
    cost_moves = abs(end.monthly_transport_cost - start.monthly_transport_cost) > 0.5
    unchanged = (
        base_mode == full_mode
        and charge_full == 0.0
        and not forced_off_car
        and not commute_moves
        and not cost_moves
    )
    if unchanged:
        lines.append(
            f"This policy does not change your daily commute: you neither pay a charge "
            f"nor change how you travel (you {mode_name.get(base_mode, base_mode)})."
        )
        return lines

    # A transit rider who keeps their mode but gains from the reinvested revenue.
    if base_mode == full_mode == TRANSIT and charge_full == 0.0 and pt_share > 0.0 and (commute_moves or cost_moves):
        lines.append(
            f"You already take public transit and pay no charge. Revenue reinvested in "
            f"public transport phases in a service uplift from around month "
            f"{adaptation.transit_lag_months:g}: your commute eases from "
            f"{start.commute_minutes_one_way:g} to {end.commute_minutes_one_way:g} min and "
            f"your monthly cost from ${start.monthly_transport_cost:g} to "
            f"${end.monthly_transport_cost:g} over the following years."
        )
        lines.append(
            f"On balance you end up {end.stance} the policy (support {end.policy_support:+.2f}) "
            "as a household that benefits from better transit at no extra cost."
        )
        return lines

    if charge_full > 0.0:
        monthly_charge = _monthly(charge_full, params)
        lines.append(
            f"You drive into the central district, so you pay the cordon charge "
            f"(~${charge_full:g} each way, about ${monthly_charge:,.0f}/month)."
        )
    if exempt_benefit:
        lines.append(
            "You qualify for the charge exemption, so you can still drive into the "
            "centre without paying the charge."
        )
    if forced_off_car:
        lines.append(
            f"Cars are banned from the central district, so you can no longer drive in "
            f"and switch to {mode_name.get(full_mode, full_mode)}."
        )
    elif base_mode != full_mode:
        lines.append(
            f"The policy makes {mode_name.get(full_mode, full_mode)} the cheaper option "
            f"for you than driving, so you switch from {base_mode} to {full_mode}."
        )

    # The characteristic worse-before-better arc from the transit capacity lag.
    if pt_share > 0.0 and (full_mode == TRANSIT or behav_mode == TRANSIT):
        peak = max(trajectory, key=lambda s: s.commute_minutes_one_way)
        final = trajectory[-1]
        lag = adaptation.transit_lag_months
        if peak.commute_minutes_one_way > final.commute_minutes_one_way + 0.5:
            lines.append(
                f"Bus capacity initially lags demand, so your commute rises to about "
                f"{peak.commute_minutes_one_way:g} min around {peak.label}. The revenue-"
                f"funded service uplift starts entering operation around month {lag:g} and "
                f"phases in over the following years, easing it back to about "
                f"{final.commute_minutes_one_way:g} min by {final.label}."
            )
        else:
            lines.append(
                "Revenue reinvested in public transport funds a service uplift that "
                f"phases in from around month {lag:g}, improving your transit option over time."
            )

    end = trajectory[-1]
    lines.append(
        f"On balance you end up {end.stance} the policy (support {end.policy_support:+.2f}) "
        "given your material impact and how fair the policy feels for a household like yours."
    )
    return lines


# --------------------------------------------------------------------------- #
# Sample picker (policy-independent)
# --------------------------------------------------------------------------- #


def sample_citizens(limit: int = 6, params: BaselineParams = DEFAULT_PARAMS) -> list[CitizenSample]:
    """A small, diverse, deterministic set of households for a UI picker (SPEC §17).

    Policy-independent — describes the synthetic population only. Picks the
    lowest-``agent_id`` CBD-commuting car driver in each income band (falling back
    to any household in that band), so the picker spans the income spectrum.
    """
    agents = dataset.population_agents()
    cbd = dataset.cbd_zone_ids()
    bands = ["low", "lower-middle", "middle", "upper-middle", "upper"]

    picked: list[CitizenSample] = []
    for band in bands:
        in_band = [a for a in agents if a["income_band"] == band]
        if not in_band:
            continue
        cbd_cars = [
            a for a in in_band
            if a["commutes_into_cbd"] and a["car_access"]
            and pick_mode(mode_options(a, params)) == CAR
        ]
        pool = cbd_cars or in_band
        chosen = min(pool, key=lambda a: a["agent_id"])
        base_mode = pick_mode(mode_options(chosen, params))
        picked.append(
            CitizenSample(
                agent_id=chosen["agent_id"],
                label=(
                    f"{chosen['occupation']}, {band} income, "
                    f"{'CBD commuter' if chosen['commutes_into_cbd'] else 'local commuter'}"
                ),
                income_band=band,
                occupation=str(chosen["occupation"]),
                home_zone=str(chosen["home_zone"]),
                commutes_into_cbd=bool(chosen["commutes_into_cbd"]),
                baseline_mode=base_mode,
            )
        )
        if len(picked) >= limit:
            break
    return picked
