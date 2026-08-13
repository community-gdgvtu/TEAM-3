"""Rank a caller-supplied shortlist of policies (SPEC §21/§22).

Reuses the optimiser's per-candidate evaluation verbatim (single source of truth
for the simulated metrics + Estimated cost proxy), then layers a transparent,
caller-weighted composite score and a Pareto-dominance read on top. Deterministic;
no LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from ..baseline.model import compute_baseline
from ..baseline.schema import Checkpoint
from ..optimiser.schema import Candidate, CandidateConfig
from ..optimiser.search import (
    COST_MODEL,
    OBJECTIVE_AXES,
    _apply_constraints,
    _best_balanced,
    _evaluate,
    _objective_vector,
    _pareto,
    _reference_gc,
)
from ..policy import compile_policy
from ..policy.dsl import InterventionType, PolicyDSL
from ..simulation.shocks import Shocks, apply_shocks
from .schema import (
    NormalizedScores,
    PolicyEntry,
    RankedPolicy,
    ShortlistRecommendations,
    ShortlistResult,
    Weights,
)

# Composite axes: (attribute, weight-field, higher_is_better).
_AXES: list[tuple[str, str, bool]] = [
    ("emissions_reduction_pct", "emissions", True),
    ("avg_commute_increase_pct", "commute", False),
    ("low_income_burden_pct", "equity", False),
    ("net_support", "support", True),
    ("est_cost", "cost", False),
]


def _derive_config(policy: PolicyDSL) -> CandidateConfig:
    """Project a full Policy DSL onto the optimiser's candidate knobs."""
    itype = policy.intervention.type
    exempt = any("low" in e.lower() and "income" in e.lower() for e in policy.exemptions)
    return CandidateConfig(
        intervention_type=itype.value,
        charge_amount=policy.intervention.amount,
        public_transport_share=policy.revenue_allocation.public_transport,
        exempt_low_income=exempt,
        pedestrianised=(itype == InterventionType.pedestrianisation),
    )


def _resolve_entry(entry: PolicyEntry, index: int) -> tuple[PolicyDSL, str, str]:
    """Return (policy, label, source) for one shortlist entry.

    Text entries are compiled by the *real* compiler; DSL entries are used as-is.
    Every policy gets a stable, collision-free id so rows never merge.
    """
    if entry.text is not None:
        policy = compile_policy(entry.text).policy.model_copy(deep=True)
        source = "compiled_from_text"
        default_label = entry.text.strip()
    else:
        policy = entry.policy.model_copy(deep=True)  # type: ignore[union-attr]
        source = "provided_dsl"
        default_label = policy.id
    policy.id = f"cand_{index:02d}"
    label = (entry.label or default_label).strip() or policy.id
    return policy, label, source


def _normalize_weights(weights: Weights | None) -> Weights:
    w = weights or Weights()
    total = w.emissions + w.commute + w.equity + w.support + w.cost
    if total <= 0:
        # Degenerate all-zero weights → fall back to equal weighting.
        return Weights()
    return Weights(
        emissions=round(w.emissions / total, 6),
        commute=round(w.commute / total, 6),
        equity=round(w.equity / total, 6),
        support=round(w.support / total, 6),
        cost=round(w.cost / total, 6),
    )


def _normalized_axis(values: list[float], higher_is_better: bool) -> list[float]:
    """Min–max normalise so 1.0 = best on this axis within the shortlist."""
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [0.5 for _ in values]  # all tied → neutral
    span = hi - lo
    if higher_is_better:
        return [(v - lo) / span for v in values]
    return [(hi - v) / span for v in values]


def _dominator_of(target: Candidate, pool: list[Candidate]) -> Candidate | None:
    """Any policy that dominates ``target`` (≤ on every objective, < on one)."""
    tv = _objective_vector(target)
    for other in pool:
        if other.policy_id == target.policy_id:
            continue
        ov = _objective_vector(other)
        if all(ov[k] <= tv[k] for k in range(len(tv))) and any(ov[k] < tv[k] for k in range(len(tv))):
            return other
    return None


def rank_shortlist(
    policies: list[PolicyEntry],
    weights: Weights | None = None,
    objective: dict | None = None,
    constraints: dict | None = None,
    *,
    shocks: Shocks | None = None,
) -> ShortlistResult:
    """Simulate and rank a caller-supplied shortlist of candidate policies."""
    objective = objective or {}
    constraints = constraints or {}
    norm_weights = _normalize_weights(weights)

    params, _trend = apply_shocks(shocks)
    base = compute_baseline(params)
    ref_all, ref_low = _reference_gc()

    # Resolve + simulate each entry (reuse the optimiser's exact metric math).
    resolved = [_resolve_entry(entry, i) for i, entry in enumerate(policies)]
    labels = {policy.id: label for policy, label, _ in resolved}
    sources = {policy.id: source for policy, _, source in resolved}
    specs = [(policy.intervention.type.value, _derive_config(policy), policy) for policy, _, _ in resolved]
    candidates = _evaluate(specs, base, params, ref_all, ref_low)
    for c in candidates:
        c.label = labels[c.policy_id]

    _apply_constraints(candidates, objective, constraints)
    feasible = [c for c in candidates if c.feasible]
    pool = feasible if feasible else candidates

    # Pareto dominance over the working pool.
    front = _pareto(pool)
    front_ids = {c.policy_id for c in front}
    for c in candidates:
        c.pareto = c.policy_id in front_ids

    # Composite score: normalise each axis across the shortlist, weighted-sum.
    axis_norms: dict[str, list[float]] = {}
    for attr, _wf, higher in _AXES:
        axis_norms[attr] = _normalized_axis([getattr(c.metrics, attr) for c in candidates], higher)

    ranked: list[RankedPolicy] = []
    for i, c in enumerate(candidates):
        norms = {attr: axis_norms[attr][i] for attr, _wf, _h in _AXES}
        composite = sum(getattr(norm_weights, wf) * norms[attr] for attr, wf, _h in _AXES)
        notes: list[str] = []
        if not c.feasible:
            notes.append("Infeasible: " + "; ".join(c.violated_constraints))
        dom = _dominator_of(c, candidates)
        if dom is not None:
            notes.append(f"Pareto-dominated by {labels[dom.policy_id]!r} (no better on any objective).")
        ranked.append(
            RankedPolicy(
                rank=0,  # filled after sorting
                policy_id=c.policy_id,
                label=c.label,
                source=sources[c.policy_id],
                candidate=c,
                normalized=NormalizedScores(
                    emissions=round(norms["emissions_reduction_pct"], 4),
                    commute=round(norms["avg_commute_increase_pct"], 4),
                    equity=round(norms["low_income_burden_pct"], 4),
                    support=round(norms["net_support"], 4),
                    cost=round(norms["est_cost"], 4),
                ),
                composite_score=round(composite, 4),
                notes=notes,
            )
        )

    # Feasible first, then by composite desc; stable tiebreak on policy_id.
    ranked.sort(key=lambda r: (not r.candidate.feasible, -r.composite_score, r.policy_id))
    for pos, r in enumerate(ranked, start=1):
        r.rank = pos

    # Recommendations + per-metric leaders over the working pool.
    recs = ShortlistRecommendations()
    leaders: dict[str, str] = {}
    if pool:
        recs.winner = next((r.policy_id for r in ranked if r.candidate.feasible), None)
        recs.greenest = max(pool, key=lambda c: c.metrics.emissions_reduction_pct).policy_id
        recs.most_equitable = min(pool, key=lambda c: c.metrics.low_income_burden_pct).policy_id
        recs.cheapest = min(pool, key=lambda c: c.metrics.est_cost).policy_id
        recs.most_supported = max(pool, key=lambda c: c.metrics.net_support).policy_id
        recs.best_balanced = _best_balanced(front)
        leaders = {
            "emissions_reduction_pct": recs.greenest,
            "avg_commute_increase_pct": min(pool, key=lambda c: c.metrics.avg_commute_increase_pct).policy_id,
            "low_income_burden_pct": recs.most_equitable,
            "net_support": recs.most_supported,
            "est_cost": recs.cheapest,
        }

    trade_offs = _build_trade_offs(ranked, candidates, labels, recs, feasible, objective, constraints)

    return ShortlistResult(
        horizon=Checkpoint(label="long-run", t_months=60.0, t_years=5.0),
        n_policies=len(candidates),
        n_feasible=len(feasible),
        constraints_satisfiable=bool(feasible),
        weights=norm_weights,
        objective=objective,
        constraints=constraints,
        ranking=ranked,
        recommendations=recs,
        per_metric_leaders=leaders,
        trade_offs=trade_offs,
        cost_model=dict(COST_MODEL),
        objective_axes=list(OBJECTIVE_AXES),
    )


def _build_trade_offs(
    ranked: list[RankedPolicy],
    candidates: list[Candidate],
    labels: dict[str, str],
    recs: ShortlistRecommendations,
    feasible: list[Candidate],
    objective: dict,
    constraints: dict,
) -> list[str]:
    """Deterministic, number-grounded trade-off narration (no LLM)."""
    out: list[str] = []
    by_id = {c.policy_id: c for c in candidates}

    if recs.winner is None:
        if constraints:
            out.append("No policy satisfies every stated constraint — ranking shown on the raw composite.")
    else:
        w = by_id[recs.winner]
        out.append(
            f"Recommended: {labels[recs.winner]!r} — best weighted score, "
            f"{w.metrics.emissions_reduction_pct:.1f}% emissions cut, "
            f"{w.metrics.low_income_burden_pct:.1f}% low-income burden, "
            f"net support {w.metrics.net_support:+.2f}."
        )
        if recs.greenest and recs.greenest != recs.winner:
            g = by_id[recs.greenest]
            out.append(
                f"Greenest option {labels[recs.greenest]!r} cuts emissions more "
                f"({g.metrics.emissions_reduction_pct:.1f}% vs {w.metrics.emissions_reduction_pct:.1f}%) "
                f"but loses on the weighted balance (burden {g.metrics.low_income_burden_pct:.1f}%, "
                f"support {g.metrics.net_support:+.2f})."
            )
        if recs.most_equitable and recs.most_equitable != recs.winner:
            e = by_id[recs.most_equitable]
            out.append(
                f"Most equitable option {labels[recs.most_equitable]!r} keeps low-income burden lowest "
                f"({e.metrics.low_income_burden_pct:.1f}%)."
            )

    dominated = [r for r in ranked if not r.candidate.pareto]
    if dominated:
        out.append(
            f"{len(dominated)} of {len(ranked)} policies are Pareto-dominated "
            "(another policy is at least as good on every objective)."
        )
    if constraints and len(feasible) < len(candidates):
        out.append(
            f"{len(candidates) - len(feasible)} of {len(candidates)} policies fail the stated constraints."
        )
    return out
