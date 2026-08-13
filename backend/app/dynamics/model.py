"""Recursive stocks-and-flows feedback engine (SPEC §7.6 System Dynamics + §19).

SPEC §19 calls recursive feedback "central to the concept" and gives the
canonical cascade::

    Policy → negative public reaction → amendment → lower charge
          → weaker traffic effect → reduced revenue → slower bus expansion
          → renewed crowding

Everything upstream in the engine produces a *single adapted end-state* (the
World-B model) or a *staged interpolation* toward it (the Time Machine). Neither
closes the loop: neither lets public opinion feed back into the *policy itself*.
This layer does.

It integrates four coupled stocks month-by-month:

* **charge** — the cordon charge actually in force. Starts at the policy's
  nominal amount and can be **cut by an endogenous amendment** when support stays
  negative (the political-response feedback SPEC §19 asks for).
* **transit_demand** — peak CBD-bound transit demand, relaxing toward the
  behavioural pull the *current* charge exerts (an ABM anchor).
* **transit_capacity** — the peak transit supply, a stock that only grows as
  cumulative reinvested revenue funds the capacity programme (with a build lag).
* **support** — net public support, relaxing toward its structural target (an
  ABM/opinion anchor at the current charge) minus a penalty for sustained
  over-capacity crowding.

The magnitudes each stock chases are all read from the deterministic agent-based
model at the charge in force (memoised per distinct charge). The coefficients
coupling them over time live in :mod:`app.dynamics.params` as documented
assumptions. No LLM touches any number (SPEC §34); same inputs ⇒ same trajectory.
"""

from __future__ import annotations

import math

from ..baseline.model import cached_baseline
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.schema import Checkpoint
from ..baseline.timeseries import _CHECKPOINTS
from ..opinion import compute_public_opinion
from ..policy.dsl import InterventionType, PolicyDSL
from ..simulation.levers import DEFAULT_SIM_PARAMS, SimParams
from ..simulation.model import compute_world_b
from .params import DEFAULT_SD_PARAMS, SystemDynamicsParams
from .schema import (
    FeedbackContrast,
    FeedbackEvent,
    StockPoint,
    SystemDynamicsResult,
)

_CHARGE_TYPES = {
    InterventionType.road_pricing,
    InterventionType.parking_levy,
    InterventionType.low_emission_zone,
}


def _relax(current: float, target: float, tau_months: float, dt: float) -> float:
    """One exponential-relaxation Euler step of ``current`` toward ``target``."""
    if tau_months <= 0:
        return target
    return current + (1.0 - math.exp(-dt / tau_months)) * (target - current)


def _confidence(years: float, p: SystemDynamicsParams) -> float:
    return round(
        max(p.confidence_floor, p.confidence_base - p.confidence_decay_per_year * years),
        2,
    )


class _StructuralAnchors:
    """ABM structural response as a function of the in-force charge, memoised.

    For each distinct charge the loop lands on we run the deterministic model once
    (behavioural-only World B) + the cohort opinion model, and cache:

    * ``demand`` — peak CBD-bound transit demand (trips/day),
    * ``revenue`` — annualised charge revenue (currency/yr),
    * ``support`` — net public support in [-1, 1].

    A congestion charge only takes a handful of values over a run (nominal plus a
    bounded number of amendment cuts), so this stays cheap while keeping every
    magnitude sourced from the ABM rather than a hand-tuned curve.
    """

    def __init__(
        self,
        policy: PolicyDSL,
        params: BaselineParams,
        sim: SimParams,
    ) -> None:
        self._policy = policy
        self._params = params
        self._sim = sim
        self._workdays = params.workdays_per_year
        self._cache: dict[float, tuple[float, float, float]] = {}

    def _policy_at(self, charge: float) -> PolicyDSL:
        p = self._policy.model_copy(deep=True)
        if p.intervention.type in _CHARGE_TYPES:
            p.intervention.amount = charge
        return p

    def at(self, charge: float) -> tuple[float, float, float]:
        key = round(charge, 4)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        pol = self._policy_at(charge)
        # Behavioural-only World B: isolates the charge's demand pull from the
        # revenue-funded capacity ramp (capacity is a separate stock here).
        wb = compute_world_b(pol, params=self._params, sim=self._sim, reinvestment=False)
        demand = float(wb.transit.peak_into_cbd_transit_trips)
        # revenue_annual = charge × priced commuters × workdays (both legs net out
        # against the per-one-way amortisation — see economy layer semantics).
        revenue = float(wb.priced_car_commuters) * charge * self._workdays
        support = compute_public_opinion(
            pol, params=self._params, sim=self._sim
        ).overall.net_support
        out = (demand, revenue, float(support))
        self._cache[key] = out
        return out


def _run_loop(
    policy: PolicyDSL,
    anchors: _StructuralAnchors,
    *,
    political_response: bool,
    nominal_charge: float,
    baseline_peak_demand: float,
    p: SystemDynamicsParams,
) -> tuple[list[StockPoint], list[FeedbackEvent], float]:
    """Integrate the coupled stocks month-by-month. Returns (checkpoints, events, cuts).

    Only the checkpoints in ``_CHECKPOINTS`` are emitted as :class:`StockPoint`s,
    but the integration itself runs every ``step_months``.
    """
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)
    dt = float(p.step_months)

    # Programme is scoped at announcement to N years of *nominal* reinvestment.
    _, nominal_revenue, _ = anchors.at(nominal_charge)
    programme_cost = p.capacity_programme_years * nominal_revenue * pt_share

    # Initial stocks (t = 0): the policy has just landed.
    demand0, _, support0 = anchors.at(nominal_charge)
    capacity0 = baseline_peak_demand * p.capacity_headroom

    charge = nominal_charge
    demand = baseline_peak_demand  # demand ramps up from the pre-policy level
    revenue_eff = 0.0
    cum_reinvest = 0.0
    capacity = capacity0
    support = support0

    cuts = 0
    months_below = 0
    checkpoint_months = {m for _, m in _CHECKPOINTS}
    checkpoint_labels = {m: lbl for lbl, m in _CHECKPOINTS}

    points: list[StockPoint] = []
    events: list[FeedbackEvent] = []
    exceeded_flagged = False
    relieved_flagged = False

    def snapshot(month: float) -> StockPoint:
        years = month / 12.0
        crowding = demand / capacity if capacity > 0 else 0.0
        return StockPoint(
            t_months=round(month, 3),
            t_years=round(years, 4),
            charge=round(charge, 3),
            support=round(support, 4),
            transit_demand=round(demand, 1),
            transit_capacity=round(capacity, 1),
            crowding=round(crowding, 4),
            cumulative_reinvestment=round(cum_reinvest, 1),
            annual_revenue=round(anchors.at(charge)[1], 1),
            confidence=_confidence(years, p),
        )

    if 0 in checkpoint_months:
        points.append(snapshot(0.0))

    month = 0.0
    while month < p.horizon_months:
        month += dt
        years = month / 12.0

        # --- structural targets at the in-force charge (ABM anchors) -------
        tgt_demand, tgt_revenue, tgt_support_struct = anchors.at(charge)

        # --- demand flow: relax toward the charge's behavioural pull -------
        demand = _relax(demand, tgt_demand, p.behaviour_tau_months, dt)

        # --- revenue flow + reinvestment stock -----------------------------
        revenue_eff = _relax(revenue_eff, tgt_revenue, p.revenue_tau_months, dt)
        cum_reinvest += revenue_eff * pt_share * (dt / 12.0)

        # --- capacity supply stock: funded, lagged, built over time --------
        if month >= p.capacity_lag_months and programme_cost > 0:
            completion = min(1.0, cum_reinvest / programme_cost)
        else:
            completion = 0.0
        capacity_target = capacity0 * (1.0 + p.max_capacity_uplift * completion)
        capacity = _relax(capacity, capacity_target, p.capacity_build_tau_months, dt)

        # --- crowding + support dynamics -----------------------------------
        crowding = demand / capacity if capacity > 0 else 0.0
        over = max(0.0, crowding - p.crowding_onset)
        support_target = max(-1.0, min(1.0, tgt_support_struct - p.crowding_penalty * over))
        support = _relax(support, support_target, p.support_tau_months, dt)

        conf = _confidence(years, p)

        # --- structured feedback events ------------------------------------
        if over > 0 and not exceeded_flagged:
            exceeded_flagged = True
            relieved_flagged = False
            events.append(
                FeedbackEvent(
                    t_months=round(month, 1),
                    type="capacity_exceeded",
                    label="Peak transit demand overtook funded capacity",
                    cause_chain=[
                        "charge shifts car commuters onto transit",
                        "transit demand rises faster than revenue-funded capacity",
                        "peak crowding exceeds network headroom",
                    ],
                    before={"crowding_onset": p.crowding_onset},
                    after={"crowding": round(crowding, 3), "capacity": round(capacity, 1)},
                    confidence=conf,
                )
            )
        if exceeded_flagged and not relieved_flagged and crowding <= p.crowding_onset:
            relieved_flagged = True
            exceeded_flagged = False
            events.append(
                FeedbackEvent(
                    t_months=round(month, 1),
                    type="crowding_relieved",
                    label="Funded capacity caught up with transit demand",
                    cause_chain=[
                        "reinvested revenue completes capacity programme",
                        "capacity overtakes peak demand",
                        "over-capacity crowding clears",
                    ],
                    before={},
                    after={"crowding": round(crowding, 3), "capacity": round(capacity, 1)},
                    confidence=conf,
                )
            )

        # --- endogenous political response (SPEC §19) ----------------------
        if support < p.political_threshold:
            months_below += dt
        else:
            months_below = 0.0
        if (
            political_response
            and cuts < p.max_amendments
            and months_below >= p.patience_months
            and charge > p.charge_floor
        ):
            old_charge = charge
            charge = max(p.charge_floor, charge * p.charge_cut_factor)
            cuts += 1
            months_below = 0.0
            new_demand, new_rev, _ = anchors.at(charge)
            events.append(
                FeedbackEvent(
                    t_months=round(month, 1),
                    type="amendment",
                    label=f"Endogenous amendment: charge cut {old_charge:g} → {charge:g}",
                    cause_chain=[
                        "sustained negative public support",
                        "political pressure forces an amendment",
                        "cordon charge is cut",
                        "weaker price signal → smaller mode shift → less transit demand",
                        "lower charge → reduced revenue → slower capacity expansion",
                    ],
                    before={
                        "charge": round(old_charge, 3),
                        "support": round(support, 3),
                        "annual_revenue": round(tgt_revenue, 1),
                    },
                    after={
                        "charge": round(charge, 3),
                        "target_transit_demand": round(new_demand, 1),
                        "annual_revenue": round(new_rev, 1),
                    },
                    confidence=conf,
                )
            )

        # --- emit at checkpoints -------------------------------------------
        m_int = int(round(month))
        if m_int in checkpoint_months and abs(month - m_int) < dt / 2.0:
            _ = checkpoint_labels  # labels available if a labelled series is needed
            points.append(snapshot(float(m_int)))

    return points, events, float(cuts)


def _loop_description(policy: PolicyDSL, has_charge: bool) -> list[str]:
    if has_charge:
        return [
            "Congestion charge lands → price-sensitive commuters switch to transit",
            "Peak transit demand rises; charge revenue is collected",
            "Revenue is reinvested → transit capacity expands (with a build lag)",
            "If demand outpaces capacity → over-capacity crowding degrades support",
            "Sustained negative support → an amendment cuts the charge",
            "Lower charge → weaker mode shift → less revenue → slower capacity growth",
            "→ crowding can return: the recursive loop SPEC §19 calls central",
        ]
    return [
        "Access restriction lands → CBD-bound car trips are displaced to transit/walk",
        "Peak transit demand rises with little charge revenue to fund capacity",
        "Capacity lags demand → crowding pressures public support",
        "(No charge to amend: the political-response arm of the loop is inert here)",
    ]


def build_system_dynamics(
    policy: PolicyDSL,
    *,
    political_response: bool = True,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    p: SystemDynamicsParams = DEFAULT_SD_PARAMS,
) -> SystemDynamicsResult:
    """Run the recursive stock-flow feedback loop for ``policy`` (SPEC §7.6/§19).

    Always integrates both the requested configuration and its toggle-counterpart
    so the result can contrast closed-loop (political response ON) vs open-loop
    (OFF) — the concrete demonstration of why recursive feedback matters (§19).
    """
    baseline = cached_baseline()
    baseline_peak_demand = float(baseline.transit.peak_into_cbd_transit_trips)
    anchors = _StructuralAnchors(policy, params, sim)

    has_charge = (
        policy.intervention.type in _CHARGE_TYPES
        and bool(policy.intervention.amount)
        and float(policy.intervention.amount or 0.0) > 0.0
    )
    nominal_charge = float(policy.intervention.amount or 0.0) if has_charge else 0.0

    primary_points, events, cuts = _run_loop(
        policy,
        anchors,
        political_response=political_response and has_charge,
        nominal_charge=nominal_charge,
        baseline_peak_demand=baseline_peak_demand,
        p=p,
    )
    # Counterfactual toggle for the contrast (same deterministic model).
    other_points, _, _ = _run_loop(
        policy,
        anchors,
        political_response=(not political_response) and has_charge,
        nominal_charge=nominal_charge,
        baseline_peak_demand=baseline_peak_demand,
        p=p,
    )

    primary_final = primary_points[-1]
    other_final = other_points[-1]
    closed_final = primary_final if political_response else other_final
    open_final = other_final if political_response else primary_final

    def contrast(metric: str, closed: float, openv: float, better_low: bool) -> FeedbackContrast:
        delta = round(closed - openv, 4)
        if abs(delta) < 1e-6:
            interp = "Recursive feedback did not change this outcome for this policy."
        else:
            interp = (
                "Recursive political feedback "
                + ("lowered" if delta < 0 else "raised")
                + f" the long-run {metric.replace('_', ' ')} versus an identical run "
                "with the amendment rule switched off."
            )
        return FeedbackContrast(
            metric=metric,
            closed_loop=round(closed, 4),
            open_loop=round(openv, 4),
            delta=delta,
            interpretation=interp,
        )

    contrasts = [
        contrast("charge", closed_final.charge, open_final.charge, True),
        contrast("support", closed_final.support, open_final.support, False),
        contrast("crowding", closed_final.crowding, open_final.crowding, True),
        contrast(
            "transit_capacity",
            closed_final.transit_capacity,
            open_final.transit_capacity,
            False,
        ),
    ]

    anchor_dump = {
        "baseline_peak_transit_demand": round(baseline_peak_demand, 1),
        "baseline_capacity": round(baseline_peak_demand * p.capacity_headroom, 1),
        "nominal_charge": nominal_charge,
        "structural_at_nominal": (
            {
                "peak_transit_demand": round(anchors.at(nominal_charge)[0], 1),
                "annual_revenue": round(anchors.at(nominal_charge)[1], 1),
                "net_support": round(anchors.at(nominal_charge)[2], 4),
            }
            if has_charge
            else {}
        ),
        "provenance": "ABM anchors Simulated; dynamics coefficients Estimated",
    }

    return SystemDynamicsResult(
        policy_id=policy.id,
        political_response_enabled=political_response and has_charge,
        loop_description=_loop_description(policy, has_charge),
        trajectory=primary_points,
        feedback_events=events,
        contrast=contrasts,
        final_state=primary_final,
        amendments_triggered=int(cuts),
        anchors=anchor_dump,
        params=p.as_dict(),
        not_modelled=[
            "Continuous charge optimisation (amendments are discrete cuts, not a controller)",
            "Ridership suppression from crowding (demand stays latent; crowding hits support only)",
            "Capacity depreciation / operating-cost drag on the reinvestment stock",
            "Exogenous shocks over the horizon (see /simulate shocks for stress tests)",
            "Spatial detail — a single cordon-level aggregate, not per-corridor (needs §7.7)",
        ],
    )
