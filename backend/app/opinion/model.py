"""Deterministic cohort opinion model (ROADMAP M6, SPEC §13).

For each synthetic micro-agent the model combines three transparent signals into
a latent support score and then a per-agent opinion distribution:

* **Material experience** — the change in the agent's *own* generalized travel
  cost between World A and World B (straight from the agent-based mode-choice
  model). Worse off ⇒ opposition.
* **Perceived fairness** — regressivity of an unexempted flat charge on lower
  incomes, the benefit of an exemption, goodwill from revenue reinvested in
  transit, and the coercion of a car ban.
* **Ideological prior** — a small, transparent lean by income band.

Agents are aggregated into cohorts (income band × geography × travel mode) and
overall, each reported as a distribution over the six SPEC §13 buckets.

Guardrail (SPEC §34): the material signal is the deterministic model's output and
the whole pipeline is LLM-free → :class:`MetricTag.simulated`.
"""

from __future__ import annotations

import math

from .. import dataset
from ..baseline.model import CAR, mode_options, pick_mode
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..policy.dsl import PolicyDSL
from ..simulation.levers import DEFAULT_SIM_PARAMS, SimParams, derive_levers
from ..simulation.model import policy_mode_options
from .params import DEFAULT_OPINION_PARAMS, OpinionParams
from .schema import CohortOpinion, OpinionDistribution, PublicOpinion

_LOW_BANDS = {"low", "lower-middle"}

# Bucket centres on the latent support axis [-1, 1].
_BUCKETS = (
    ("strong_support", 1.0),
    ("support", 0.5),
    ("neutral", 0.0),
    ("oppose", -0.5),
    ("strong_oppose", -1.0),
)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _agent_support(
    agent: dict,
    base_cost: float,
    pol_cost: float,
    pol_mode: str,
    paid_charge: bool,
    exempt_benefit: bool,
    forced_off_car: bool,
    levers,
    pt_share: float,
    op: OpinionParams,
) -> tuple[float, float, float]:
    """Return (material_impact_minutes, fairness_signal, latent_support)."""
    # Material: positive gc_delta = worse off = less support.
    gc_delta = pol_cost - base_cost
    material = _clamp(-gc_delta / op.material_scale_min, -1.0, 1.0)

    # Fairness.
    fairness = 0.0
    band = agent["income_band"]
    if paid_charge and band in _LOW_BANDS:
        fairness -= op.fairness_regressive
    if exempt_benefit:
        fairness += op.fairness_exemption
    if pt_share > 0.0:
        if pol_mode != CAR:
            fairness += op.fairness_reinvest * pt_share
        fairness += op.fairness_reinvest_general * pt_share
    if forced_off_car:
        fairness -= op.fairness_coercion
    fairness = _clamp(fairness, -1.0, 1.0)

    prior = op.prior_for(band)
    support = _clamp(
        op.w_material * material + op.w_fairness * fairness + op.w_prior * prior,
        -1.0,
        1.0,
    )
    return gc_delta, fairness, support


def _distribution(support: float, salience: float, op: OpinionParams) -> list[float]:
    """Per-agent probability over [strong_support, support, neutral, oppose, strong_oppose, uncertain]."""
    uncertain = _clamp(
        op.uncertain_base * (1.0 - salience), op.uncertain_floor, op.uncertain_cap
    )
    weights = [
        math.exp(-((support - c) ** 2) / (2.0 * op.opinion_sigma**2)) for _, c in _BUCKETS
    ]
    total = sum(weights)
    scaled = [(1.0 - uncertain) * w / total for w in weights]
    scaled.append(uncertain)
    return scaled


def _blank_acc() -> list[float]:
    return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def _finalise(acc: list[float], n: int) -> OpinionDistribution:
    if n == 0:
        return OpinionDistribution()
    frac = [round(v / n, 4) for v in acc]
    net = round(frac[0] + frac[1] - frac[3] - frac[4], 4)
    return OpinionDistribution(
        strong_support=frac[0],
        support=frac[1],
        neutral=frac[2],
        oppose=frac[3],
        strong_oppose=frac[4],
        uncertain=frac[5],
        net_support=net,
    )


def compute_public_opinion(
    policy: PolicyDSL,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    op: OpinionParams = DEFAULT_OPINION_PARAMS,
) -> PublicOpinion:
    """Run the deterministic cohort opinion model for ``policy``."""
    agents = dataset.population_agents()
    cbd = dataset.cbd_zone_ids()
    levers = derive_levers(policy, params=params, sim=sim)
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)

    overall_acc = _blank_acc()
    # cohort key -> [acc(6), n, sum_material, sum_fairness, sum_support, meta]
    cohorts: dict[str, dict] = {}

    for a in agents:
        base_opts = mode_options(a, params)
        base_mode = pick_mode(base_opts)
        base_cost = base_opts[base_mode]

        pol_opts = policy_mode_options(a, levers, cbd, params)
        pol_mode = pick_mode(pol_opts)
        pol_cost = pol_opts[pol_mode]

        into_cbd = a["commutes_into_cbd"]
        would_pay = (
            into_cbd
            and levers.charge_per_one_way > 0
            and a["car_access"]
            and not (into_cbd and levers.car_banned_in_cbd)
        )
        exempt = levers.is_exempt(a, cbd)
        paid_charge = pol_mode == CAR and into_cbd and levers.charge_per_one_way > 0 and not exempt
        exempt_benefit = would_pay and exempt and pol_mode == CAR
        forced_off_car = (
            base_mode == CAR and into_cbd and levers.car_banned_in_cbd and pol_mode != CAR
        )

        gc_delta, fairness, support = _agent_support(
            a, base_cost, pol_cost, pol_mode, paid_charge, exempt_benefit,
            forced_off_car, levers, pt_share, op,
        )
        dist = _distribution(support, a.get("policy_salience", 0.3), op)

        for i in range(6):
            overall_acc[i] += dist[i]

        geography = "inbound" if into_cbd else "local"
        key = f"{a['income_band']}|{geography}|{base_mode}"
        c = cohorts.get(key)
        if c is None:
            c = {
                "acc": _blank_acc(),
                "n": 0,
                "material": 0.0,
                "fairness": 0.0,
                "support": 0.0,
                "income_band": a["income_band"],
                "geography": geography,
                "travel_mode": base_mode,
            }
            cohorts[key] = c
        for i in range(6):
            c["acc"][i] += dist[i]
        c["n"] += 1
        c["material"] += gc_delta
        c["fairness"] += fairness
        c["support"] += support

    n_total = len(agents)
    cohort_out: list[CohortOpinion] = []
    for key, c in cohorts.items():
        n = c["n"]
        cohort_out.append(
            CohortOpinion(
                key=key,
                income_band=c["income_band"],
                geography=c["geography"],
                travel_mode=c["travel_mode"],
                size=n,
                mean_material_impact=round(c["material"] / n, 3),
                mean_fairness=round(c["fairness"] / n, 3),
                mean_support=round(c["support"] / n, 3),
                distribution=_finalise(c["acc"], n),
            )
        )
    # Stable, meaningful ordering: most opposed cohorts first.
    cohort_out.sort(key=lambda co: co.mean_support)

    return PublicOpinion(
        policy_id=policy.id,
        population=n_total,
        overall=_finalise(overall_acc, n_total),
        cohorts=cohort_out,
        params=op.as_dict(),
    )
