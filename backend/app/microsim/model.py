"""Distributional microsimulation (SPEC §7.3).

SPEC §7.3 asks the microsimulation layer to answer, at person level: *Who gains?
Who loses? By how much? Which decile? Which neighbourhood? Which household type?*

This computes, for every synthetic commuter, the change in their **minimum
generalized cost** between World A (baseline) and World B (policy) using the same
deterministic mode-choice model as ``/simulate`` — so a commuter who re-optimises
(switches mode) is credited with the cost of their *new* best option, not a
counterfactual they would never take. That per-agent welfare change (in
minutes-equivalent) plus the out-of-pocket charge each agent actually pays are
rolled up across income deciles, household types, home geography and occupation.

Guardrail (SPEC §34): entirely deterministic and LLM-free. The generalized-cost
change is Simulated; the money-equivalent conversion uses a documented Estimated
population value-of-time (``money_to_minutes``).
"""

from __future__ import annotations

from .. import dataset
from ..baseline.model import CAR, mode_options, pick_mode
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..policy.dsl import PolicyDSL
from ..simulation.levers import (
    DEFAULT_SIM_PARAMS,
    PolicyLevers,
    SimParams,
    derive_levers,
)
from ..simulation.model import policy_mode_options
from .schema import ConstraintCheck, GroupImpact, MicrosimReport

_EPS = 0.01  # minutes-equiv threshold for "meaningfully changed"
_BURDEN_EPS = 1e-9  # tolerance (percentage points) for the constraint-compliance test


def _round(x: float, d: int = 2) -> float:
    return round(float(x), d)


def _pct(n: int, total: int) -> float:
    return _round(100.0 * n / total, 1) if total else 0.0


class _AgentImpact:
    """Per-agent computed impact (kept lightweight, not a pydantic model)."""

    __slots__ = (
        "gc_change_min",
        "money_equiv_daily",
        "charge_paid_daily",
        "burden_pct",
        "switched",
    )

    def __init__(self, gc_change_min, money_equiv_daily, charge_paid_daily, burden_pct, switched):
        self.gc_change_min = gc_change_min
        self.money_equiv_daily = money_equiv_daily
        self.charge_paid_daily = charge_paid_daily
        self.burden_pct = burden_pct
        self.switched = switched


def _agent_impact(
    agent: dict,
    levers: PolicyLevers,
    cbd: set[str],
    params: BaselineParams,
    sim: SimParams,
) -> _AgentImpact:
    opts_a = mode_options(agent, params)
    opts_b = policy_mode_options(agent, levers, cbd, params)
    mode_a = pick_mode(opts_a)
    mode_b = pick_mode(opts_b)
    gc_change = opts_b[mode_b] - opts_a[mode_a]

    trips = params.trips_per_commuter_per_day
    # Money-equivalent per day via the population value-of-time (money_to_minutes
    # is minutes of disutility per currency unit → invert to currency per minute).
    money_equiv_daily = gc_change * trips / max(1e-9, params.money_to_minutes)

    # Out-of-pocket charge actually paid (only if they still drive into the cordon).
    charge_paid_daily = 0.0
    if (
        mode_b == CAR
        and agent["commutes_into_cbd"]
        and levers.charge_per_one_way > 0
        and not levers.is_exempt(agent, cbd)
    ):
        charge_paid_daily = levers.charge_per_one_way * trips

    income_annual = max(1.0, float(agent.get("income", 0.0)) * 12.0)
    burden_pct = 100.0 * (charge_paid_daily * params.workdays_per_year) / income_annual

    return _AgentImpact(
        gc_change_min=gc_change,
        money_equiv_daily=money_equiv_daily,
        charge_paid_daily=charge_paid_daily,
        burden_pct=burden_pct,
        switched=mode_a != mode_b,
    )


def _group_impact(label: str, impacts: list[_AgentImpact]) -> GroupImpact:
    n = len(impacts)
    if n == 0:
        return GroupImpact(
            group=label, agents=0, mean_gc_change_min=0.0, mean_money_equiv_daily=0.0,
            mean_charge_paid_daily=0.0, mean_burden_pct_income=0.0,
            pct_worse_off=0.0, pct_better_off=0.0, pct_switched_mode=0.0,
        )
    worse = sum(1 for i in impacts if i.gc_change_min > _EPS)
    better = sum(1 for i in impacts if i.gc_change_min < -_EPS)
    switched = sum(1 for i in impacts if i.switched)
    return GroupImpact(
        group=label,
        agents=n,
        mean_gc_change_min=_round(sum(i.gc_change_min for i in impacts) / n, 2),
        mean_money_equiv_daily=_round(sum(i.money_equiv_daily for i in impacts) / n, 3),
        mean_charge_paid_daily=_round(sum(i.charge_paid_daily for i in impacts) / n, 3),
        mean_burden_pct_income=_round(sum(i.burden_pct for i in impacts) / n, 3),
        pct_worse_off=_pct(worse, n),
        pct_better_off=_pct(better, n),
        pct_switched_mode=_pct(switched, n),
    )


def _household_bucket(size: int) -> str:
    if size <= 1:
        return "1 (single)"
    if size >= 4:
        return "4+"
    return str(size)


def build_microsim_report(
    policy: PolicyDSL,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
) -> MicrosimReport:
    """Run the per-agent distributional microsimulation (SPEC §7.3)."""
    agents = dataset.population_agents()
    cbd = dataset.cbd_zone_ids()
    levers = derive_levers(policy, params=params, sim=sim)

    impacts = [_agent_impact(a, levers, cbd, params, sim) for a in agents]
    n = len(agents)

    winners = sum(1 for i in impacts if i.gc_change_min < -_EPS)
    losers = sum(1 for i in impacts if i.gc_change_min > _EPS)
    unaffected = n - winners - losers
    payers = [i for i in impacts if i.charge_paid_daily > 0]

    # --- Income deciles (rank agents by income, split into ten) ------------
    order = sorted(range(n), key=lambda k: float(agents[k].get("income", 0.0)))
    decile_of: list[int] = [0] * n
    for rank, k in enumerate(order):
        decile_of[k] = min(9, rank * 10 // n) if n else 0
    decile_groups: list[list[_AgentImpact]] = [[] for _ in range(10)]
    for k in range(n):
        decile_groups[decile_of[k]].append(impacts[k])
    decile_labels = [
        "Decile 1 (lowest income)", "Decile 2", "Decile 3", "Decile 4", "Decile 5",
        "Decile 6", "Decile 7", "Decile 8", "Decile 9", "Decile 10 (highest income)",
    ]
    by_decile = [_group_impact(decile_labels[d], decile_groups[d]) for d in range(10)]

    # Regressivity: burden on the bottom decile vs the top decile.
    bottom_burden = by_decile[0].mean_burden_pct_income
    top_burden = by_decile[9].mean_burden_pct_income
    regressivity = _round(bottom_burden / top_burden, 2) if top_burden > 0 else (
        999.0 if bottom_burden > 0 else 0.0
    )
    if regressivity == 0.0:
        regressivity_note = "No cordon charge is paid, so there is no charge-burden gradient."
    elif regressivity >= 999.0:
        regressivity_note = (
            "The lowest-income decile pays a charge burden while the highest pays "
            "effectively none — strongly regressive on out-of-pocket cost."
        )
    elif regressivity > 1.2:
        regressivity_note = (
            f"The charge burden on the lowest decile is {regressivity}× that on the "
            "highest — regressive on out-of-pocket cost (mitigable by a low-income "
            "exemption or reinvestment)."
        )
    elif regressivity < 0.83:
        regressivity_note = (
            "The charge burden is progressive — it falls harder on higher incomes."
        )
    else:
        regressivity_note = "The charge burden is roughly proportional across income deciles."

    # --- Stated-constraint compliance --------------------------------------
    # If the policy declares a cap on the low-income burden increase, actually
    # test it against the modelled outcome instead of merely asserting it (SPEC
    # §34). The baseline has no cordon charge, so the World-B out-of-pocket burden
    # on the lowest-income decile IS the increase the cap governs.
    constraint_check = None
    cap = policy.constraints.max_low_income_burden_increase_pct
    if cap is not None:
        modelled = bottom_burden  # decile-1 mean charge burden as % of income
        satisfied = modelled <= cap + _BURDEN_EPS
        margin = _round(cap - modelled, 3)
        if modelled <= _BURDEN_EPS:
            note = (
                f"The lowest-income decile bears no modelled cordon burden "
                f"(exempt or not driving into the charge), so the {cap:g}% cap holds "
                f"with the full cap as headroom."
            )
        elif satisfied:
            note = (
                f"Modelled low-income burden is {modelled:g}% of income, within the "
                f"stated {cap:g}% cap ({margin:g}pp headroom)."
            )
        else:
            note = (
                f"Modelled low-income burden is {modelled:g}% of income, EXCEEDING the "
                f"stated {cap:g}% cap by {_round(modelled - cap, 3):g}pp — the policy "
                f"violates its own equity constraint (add a low-income exemption or cut "
                f"the charge to comply)."
            )
        constraint_check = ConstraintCheck(
            name="max_low_income_burden_increase_pct",
            cap_pct=cap,
            modelled_low_income_burden_pct=modelled,
            satisfied=satisfied,
            margin_pct=margin,
            note=note,
        )

    # --- Household type ----------------------------------------------------
    hh: dict[str, list[_AgentImpact]] = {}
    for k in range(n):
        hh.setdefault(_household_bucket(int(agents[k].get("household_size", 1))), []).append(impacts[k])
    by_household = [_group_impact(f"Household size {lbl}", hh[lbl]) for lbl in sorted(hh)]

    # --- Geography (central vs outer home; plus most-affected zones) -------
    central = [impacts[k] for k in range(n) if agents[k].get("home_zone") in cbd]
    outer = [impacts[k] for k in range(n) if agents[k].get("home_zone") not in cbd]
    by_geography = [
        _group_impact("Lives in the central district", central),
        _group_impact("Lives outside the central district", outer),
    ]
    # Top-3 most-adversely-affected home zones by mean gc change.
    zone_groups: dict[str, list[_AgentImpact]] = {}
    for k in range(n):
        zone_groups.setdefault(agents[k].get("home_zone", "?"), []).append(impacts[k])
    zone_impacts = [
        _group_impact(f"Home zone {z}", g) for z, g in zone_groups.items() if len(g) >= 10
    ]
    zone_impacts.sort(key=lambda gi: gi.mean_gc_change_min, reverse=True)
    by_geography.extend(zone_impacts[:3])

    # --- Occupation --------------------------------------------------------
    occ: dict[str, list[_AgentImpact]] = {}
    for k in range(n):
        occ.setdefault(str(agents[k].get("occupation", "?")), []).append(impacts[k])
    by_occupation = [_group_impact(o.replace("_", " ").title(), occ[o]) for o in sorted(occ)]
    by_occupation.sort(key=lambda gi: gi.mean_gc_change_min, reverse=True)

    # --- Named who-gains / who-loses ---------------------------------------
    hit_pool = [g for g in (by_decile + by_household + by_occupation) if g.agents > 0]
    worst = max(hit_pool, key=lambda g: g.mean_gc_change_min) if hit_pool else None
    best = min(hit_pool, key=lambda g: g.mean_gc_change_min) if hit_pool else None

    mean_payer_burden = (
        _round(sum(i.burden_pct for i in payers) / len(payers), 3) if payers else 0.0
    )

    return MicrosimReport(
        policy_id=policy.id,
        commuters=n,
        winners=winners,
        losers=losers,
        unaffected=unaffected,
        mean_gc_change_min=_round(sum(i.gc_change_min for i in impacts) / n, 3) if n else 0.0,
        payers=len(payers),
        mean_payer_burden_pct=mean_payer_burden,
        regressivity_ratio=regressivity,
        regressivity_note=regressivity_note,
        constraint_check=constraint_check,
        by_income_decile=by_decile,
        by_household_type=by_household,
        by_geography=by_geography,
        by_occupation=by_occupation,
        worst_hit=(worst.group if worst and worst.mean_gc_change_min > _EPS else "None (no group is worse off on average)"),
        biggest_winner=(best.group if best and best.mean_gc_change_min < -_EPS else "None (no group is better off on average)"),
        params={
            "money_to_minutes": params.money_to_minutes,
            "trips_per_commuter_per_day": params.trips_per_commuter_per_day,
            "workdays_per_year": params.workdays_per_year,
            "value_of_time_note": "Money-equivalent uses the population value-of-time "
            "(money_to_minutes); the per-agent generalized cost weights money by each "
            "agent's own price sensitivity.",
        },
        not_modelled=[
            "Only commuter travel welfare is measured — not wider household budgets, "
            "labour-supply changes or business costs.",
            "The money-equivalent uses a single population value-of-time; true "
            "compensating variation is agent-specific and only approximated here.",
            "Income is the synthetic agent income; no tax/benefit interaction or "
            "in-kind gains from reinvested revenue are attributed back to individuals.",
            "Deciles/household/occupation reflect the synthetic population sample, "
            "not a real administrative microdata register.",
        ],
    )
