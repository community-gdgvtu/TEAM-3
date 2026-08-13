"""Policy optimiser stub: grid-search → simulate → Pareto (ROADMAP stretch, SPEC §22).

Given an objective and constraints, this enumerates a small grid of candidate
interventions (congestion charge / parking levy / pedestrianisation × revenue
split × low-income exemption), simulates each with the deterministic World-B
model and the cohort opinion model, filters by the constraints and builds a
Pareto frontier over the competing objectives (emissions cut vs commute cost vs
low-income burden vs scheme cost). It then labels representative policies.

Only documented assumptions and the same structural model are used; the outcome
numbers are Simulated and the cost proxy is an Estimated, auditable constant. No
LLM is on the numeric path (SPEC §34).
"""

from __future__ import annotations

from ..baseline.model import compute_baseline, mode_options, pick_mode
from ..baseline.params import DEFAULT_PARAMS
from ..baseline.schema import Checkpoint
from ..opinion.model import _LOW_BANDS, compute_public_opinion
from ..policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from ..simulation.model import compute_world_b
from ..simulation.shocks import Shocks, apply_shocks
from .. import dataset
from .schema import (
    Candidate,
    CandidateConfig,
    CandidateMetrics,
    OptimiserResult,
    Recommendations,
)

# Illustrative, documented scheme-cost proxy (Estimated, local currency units).
# Used ONLY for the optional max_budget constraint — never simulated, never LLM.
COST_MODEL: dict[str, float] = {
    "road_pricing": 45_000_000.0,
    "low_emission_zone": 45_000_000.0,
    "parking_levy": 25_000_000.0,
    "pedestrianisation": 60_000_000.0,
    "transit_reinvest_full": 55_000_000.0,  # capital uplift at 100% reinvestment
}

# Objectives the Pareto frontier trades off (all normalised to "minimise").
OBJECTIVE_AXES = [
    "emissions_reduction_pct",  # maximised (negated for dominance)
    "avg_commute_increase_pct",
    "low_income_burden_pct",
    "est_cost",
]


def _est_cost(intervention_type: str, pt_share: float) -> float:
    base = COST_MODEL.get(intervention_type, COST_MODEL["road_pricing"])
    return round(base + pt_share * COST_MODEL["transit_reinvest_full"], 2)


def _candidate_grid() -> list[tuple[str, CandidateConfig, PolicyDSL]]:
    """Enumerate the candidate policy grid (kept small — this is a stub)."""
    specs: list[tuple[str, CandidateConfig, PolicyDSL]] = []
    idx = 0

    def _add(itype: InterventionType, amount, pt_share, exempt, pedestrian):
        nonlocal idx
        exemptions = ["low-income"] if exempt else []
        pol = PolicyDSL(
            id=f"cand_{idx:02d}",
            intervention=Intervention(
                type=itype, amount=amount, currency="local"
            ),
            exemptions=exemptions,
            revenue_allocation=RevenueAllocation(
                public_transport=pt_share, general_fund=round(1.0 - pt_share, 4)
            ),
        )
        cfg = CandidateConfig(
            intervention_type=itype.value,
            charge_amount=amount,
            public_transport_share=pt_share,
            exempt_low_income=exempt,
            pedestrianised=(itype == InterventionType.pedestrianisation),
        )
        specs.append((itype.value, cfg, pol))
        idx += 1

    # Congestion charge grid.
    for amount in (6.0, 12.0, 18.0):
        for pt_share in (0.0, 0.5, 1.0):
            for exempt in (False, True):
                _add(InterventionType.road_pricing, amount, pt_share, exempt, False)
    # Parking levy (a couple of points).
    for amount in (8.0, 14.0):
        for pt_share in (0.5, 1.0):
            _add(InterventionType.parking_levy, amount, pt_share, False, False)
    # Pedestrianisation (car ban) + reinvestment.
    for pt_share in (0.0, 0.5, 1.0):
        _add(InterventionType.pedestrianisation, None, pt_share, False, True)

    return specs


def _reference_gc() -> tuple[float, float]:
    """Baseline size-weighted generalized cost: (all commuters, low-income)."""
    agents = dataset.population_agents()
    tot = 0.0
    tot_n = 0
    low = 0.0
    low_n = 0
    for a in agents:
        opts = mode_options(a, DEFAULT_PARAMS)
        gc = opts[pick_mode(opts)]
        tot += gc
        tot_n += 1
        if a["income_band"] in _LOW_BANDS:
            low += gc
            low_n += 1
    ref_all = tot / max(1, tot_n)
    ref_low = low / max(1, low_n)
    return ref_all, ref_low


def _burden_pcts(policy: PolicyDSL, params, ref_all: float, ref_low: float) -> tuple[float, float, float]:
    """(avg_commute_increase_pct, low_income_burden_pct, net_support) via opinion cohorts."""
    op = compute_public_opinion(policy, params=params)
    all_w = 0.0
    all_n = 0
    low_w = 0.0
    low_n = 0
    for c in op.cohorts:
        all_w += c.mean_material_impact * c.size
        all_n += c.size
        if c.income_band in _LOW_BANDS:
            low_w += c.mean_material_impact * c.size
            low_n += c.size
    mean_all = all_w / max(1, all_n)
    mean_low = low_w / max(1, low_n)
    avg_pct = mean_all / ref_all * 100.0 if ref_all else 0.0
    low_pct = mean_low / ref_low * 100.0 if ref_low else 0.0
    return round(avg_pct, 3), round(low_pct, 3), round(op.overall.net_support, 4)


def _evaluate(specs, base, params, ref_all, ref_low) -> list[Candidate]:
    out: list[Candidate] = []
    base_co2 = base.emissions.daily_co2_tonnes
    base_trips = base.traffic.vehicle_trips_into_cbd
    base_transit = base.transit.peak_into_cbd_transit_trips
    for itype, cfg, pol in specs:
        b = compute_world_b(pol, params=params, reinvestment=True)
        emissions_red = (base_co2 - b.emissions.daily_co2_tonnes) / base_co2 * 100.0 if base_co2 else 0.0
        traffic_red = (base_trips - b.traffic.vehicle_trips_into_cbd) / base_trips * 100.0 if base_trips else 0.0
        transit_gain = (b.transit.peak_into_cbd_transit_trips - base_transit) / base_transit * 100.0 if base_transit else 0.0
        avg_pct, low_pct, net_support = _burden_pcts(pol, params, ref_all, ref_low)
        metrics = CandidateMetrics(
            emissions_reduction_pct=round(emissions_red, 3),
            traffic_reduction_pct=round(traffic_red, 3),
            transit_gain_pct=round(transit_gain, 3),
            avg_commute_increase_pct=avg_pct,
            low_income_burden_pct=low_pct,
            net_support=net_support,
            est_cost=_est_cost(itype, cfg.public_transport_share),
        )
        label_bits = [itype.replace("_", " ")]
        if cfg.charge_amount:
            label_bits.append(f"{cfg.charge_amount:g}/day")
        label_bits.append(f"{cfg.public_transport_share:.0%} to transit")
        if cfg.exempt_low_income:
            label_bits.append("low-income exempt")
        out.append(
            Candidate(
                policy_id=pol.id,
                label=", ".join(label_bits),
                description=[
                    f"{itype.replace('_', ' ')} intervention",
                    f"{cfg.public_transport_share:.0%} of revenue reinvested in transit",
                    ("low-income commuters exempt" if cfg.exempt_low_income else "no exemptions"),
                ],
                config=cfg,
                metrics=metrics,
                feasible=True,
                violated_constraints=[],
            )
        )
    return out


def _apply_constraints(candidates: list[Candidate], objective: dict, constraints: dict) -> None:
    """Mark each candidate feasible/infeasible against the constraints (in place)."""
    emis_target = objective.get("reduce_transport_emissions_pct")
    max_commute = constraints.get("max_average_commute_increase_pct")
    max_burden = constraints.get("max_low_income_burden_increase_pct")
    max_budget = constraints.get("max_budget")
    for c in candidates:
        viol: list[str] = []
        m = c.metrics
        if emis_target is not None and m.emissions_reduction_pct < emis_target:
            viol.append(
                f"emissions reduction {m.emissions_reduction_pct:.1f}% < target {emis_target:g}%"
            )
        if max_commute is not None and m.avg_commute_increase_pct > max_commute:
            viol.append(
                f"avg commute increase {m.avg_commute_increase_pct:.1f}% > max {max_commute:g}%"
            )
        if max_burden is not None and m.low_income_burden_pct > max_burden:
            viol.append(
                f"low-income burden {m.low_income_burden_pct:.1f}% > max {max_burden:g}%"
            )
        if max_budget is not None and m.est_cost > max_budget:
            viol.append(f"est cost {m.est_cost:,.0f} > budget {max_budget:,.0f}")
        c.violated_constraints = viol
        c.feasible = not viol


def _objective_vector(c: Candidate) -> list[float]:
    """All objectives as minimisation targets (emissions cut negated)."""
    m = c.metrics
    return [
        -m.emissions_reduction_pct,
        m.avg_commute_increase_pct,
        m.low_income_burden_pct,
        m.est_cost,
    ]


def _pareto(candidates: list[Candidate]) -> list[Candidate]:
    """Non-dominated set under the minimisation objective vectors."""
    vecs = [_objective_vector(c) for c in candidates]
    front: list[Candidate] = []
    for i, ci in enumerate(candidates):
        dominated = False
        for j, cj in enumerate(candidates):
            if i == j:
                continue
            vi, vj = vecs[i], vecs[j]
            if all(vj[k] <= vi[k] for k in range(len(vi))) and any(
                vj[k] < vi[k] for k in range(len(vi))
            ):
                dominated = True
                break
        if not dominated:
            front.append(ci)
    return front


def _best_balanced(front: list[Candidate]) -> str | None:
    """Closest to the ideal point after min-max normalising each objective."""
    if not front:
        return None
    vecs = [_objective_vector(c) for c in front]
    dims = len(vecs[0])
    lo = [min(v[k] for v in vecs) for k in range(dims)]
    hi = [max(v[k] for v in vecs) for k in range(dims)]
    best_id = None
    best_score = None
    for c, v in zip(front, vecs):
        # Normalise each objective to [0,1] (0 = best); distance to origin (ideal).
        norm = [
            (v[k] - lo[k]) / (hi[k] - lo[k]) if hi[k] > lo[k] else 0.0
            for k in range(dims)
        ]
        score = sum(x * x for x in norm)
        if best_score is None or score < best_score:
            best_score = score
            best_id = c.policy_id
    return best_id


def optimise_policy(
    objective: dict | None = None,
    constraints: dict | None = None,
    *,
    shocks: Shocks | None = None,
) -> OptimiserResult:
    """Search the candidate grid and return the feasible Pareto frontier."""
    objective = objective or {}
    constraints = constraints or {}
    params, _trend = apply_shocks(shocks)
    base = compute_baseline(params)
    ref_all, ref_low = _reference_gc()

    specs = _candidate_grid()
    candidates = _evaluate(specs, base, params, ref_all, ref_low)
    _apply_constraints(candidates, objective, constraints)

    feasible = [c for c in candidates if c.feasible]
    satisfiable = bool(feasible)
    # Pareto over the feasible set; if none feasible, fall back to all candidates.
    pool = feasible if feasible else candidates
    front = _pareto(pool)
    front_ids = {c.policy_id for c in front}
    for c in candidates:
        c.pareto = c.policy_id in front_ids

    recs = Recommendations()
    if front:
        recs.cheapest = min(front, key=lambda c: c.metrics.est_cost).policy_id
        recs.most_equitable = min(front, key=lambda c: c.metrics.low_income_burden_pct).policy_id
        recs.largest_emissions_reduction = max(
            front, key=lambda c: c.metrics.emissions_reduction_pct
        ).policy_id
        recs.best_balanced = _best_balanced(front)

    return OptimiserResult(
        objective=objective,
        constraints=constraints,
        horizon=Checkpoint(label="long-run", t_months=60.0, t_years=5.0),
        n_candidates=len(candidates),
        n_feasible=len(feasible),
        constraints_satisfiable=satisfiable,
        pareto_front=sorted(front, key=lambda c: c.metrics.emissions_reduction_pct, reverse=True),
        recommendations=recs,
        candidates=candidates,
        cost_model=dict(COST_MODEL),
        objective_axes=list(OBJECTIVE_AXES),
    )
