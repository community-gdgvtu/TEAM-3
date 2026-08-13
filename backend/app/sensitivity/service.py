"""Global one-at-a-time (OAT) sensitivity — the "tornado" analysis.

SPEC §24 (uncertainty) + §26 (explainability). The `/uncertainty` endpoint
already ranks the most-influential assumptions **for a single metric** via a
100-sample Monte-Carlo sweep. This layer answers a different, cheaper, more
decision-relevant question the minister actually asks: *across the WHOLE
dashboard, which assumption is the answer resting on?* — and does it
deterministically with a handful of re-runs instead of a stochastic fan.

Method (pure, deterministic, no LLM — SPEC §34):
  1. Run the deterministic World-A/B/Δ pipeline once at the default assumptions
     → each headline metric's default policy effect Δ(B−A) at the horizon.
  2. For each documented assumption (the SAME set the §24 uncertainty engine
     sweeps — single source of truth), re-run the pipeline with that assumption
     pinned to its plausible LOW edge, then to its HIGH edge (all others at
     default), and record the swing in EVERY metric's Δ.
  3. Per metric: a tornado (assumptions ranked by |swing|). Per assumption: an
     aggregate leverage score = its mean share of each metric's total OAT
     sensitivity — a scale-free way to rank drivers across metrics with
     different units. Assumptions that are flat on every metric for this policy
     (e.g. a fare-cut knob under a no-charge policy) are honestly flagged.

Bar length is **leverage, not likelihood**, and OAT ignores interactions — both
stated in the response's `not_modelled`. The output is Estimated (an attribution
derived from the model), never an LLM number.
"""

from __future__ import annotations

from dataclasses import replace

from ..baseline.model import compute_baseline
from ..baseline.params import BaselineParams
from ..baseline.schema import Checkpoint
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.levers import SimParams
from ..simulation.model import compute_world_b
from ..simulation.schema import DeltaTimeSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from ..uncertainty.engine import ASSUMPTIONS
from .schema import (
    AssumptionDriver,
    AssumptionSwing,
    MetricTornado,
    SensitivityResult,
)


def _apply(base_params: BaselineParams, sim_params: SimParams, overrides: dict):
    """Return (BaselineParams, SimParams) with ``overrides`` (name→value) applied.

    Mirrors the uncertainty engine's application against the SAME assumption
    contract, so a sensitivity run can never perturb a different knob than the
    fan on /uncertainty does.
    """
    base_kw = {a.field: overrides[a.name] for a in ASSUMPTIONS if a.target == "base" and a.name in overrides}
    sim_kw = {a.field: overrides[a.name] for a in ASSUMPTIONS if a.target == "sim" and a.name in overrides}
    bp = replace(base_params, **base_kw) if base_kw else base_params
    sp = replace(sim_params, **sim_kw) if sim_kw else sim_params
    return bp, sp


def _full_delta(
    policy: PolicyDSL,
    base_params: BaselineParams,
    sim_params: SimParams,
    trend: dict,
) -> DeltaTimeSeries:
    """Run the full A/B/Δ pipeline once and return every metric's Δ trajectory.

    Identical to the pipeline `/simulate`, `/uncertainty` and `/assumptions/rerun`
    run — so the sensitivity layer can never disagree with the headline numbers.
    """
    base = compute_baseline(base_params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=base_params, sim=sim_params, reinvestment=True)
    b_behav = compute_world_b(policy, params=base_params, sim=sim_params, reinvestment=False)
    b_ts = build_world_b_timeline(
        policy,
        baseline=base,
        world_b_full=b_full,
        world_b_behaviour=b_behav,
        params=base_params,
        trend=trend,
    )
    return build_delta(base_ts, b_ts)


def _horizon_index(delta: DeltaTimeSeries, horizon_months: float | None) -> int:
    checkpoints = [c.t_months for c in delta.checkpoints]
    if not checkpoints:
        return 0
    if horizon_months is None:
        return checkpoints.index(60.0) if 60.0 in checkpoints else len(checkpoints) - 1
    return min(range(len(checkpoints)), key=lambda i: abs(checkpoints[i] - horizon_months))


def _delta_at(delta: DeltaTimeSeries, h_idx: int) -> dict[str, float]:
    """metric key → Δ(B−A) at the horizon index."""
    return {s.key: s.points[h_idx].delta for s in delta.series}


_EPS = 1e-9


def run_sensitivity(
    policy: PolicyDSL,
    *,
    shocks: Shocks | None = None,
    horizon_months: float | None = None,
    metric_keys: list[str] | None = None,
) -> SensitivityResult:
    """Global one-at-a-time sensitivity tornado across all headline metrics."""
    base_params, trend = apply_shocks(shocks)
    sim_params = SimParams()

    # --- Default run: establishes checkpoints, labels, and the reference Δ. ---
    default_delta = _full_delta(policy, base_params, sim_params, trend)
    h_idx = _horizon_index(default_delta, horizon_months)
    horizon_cp = default_delta.checkpoints[h_idx]

    series = list(default_delta.series)
    if metric_keys:
        wanted = set(metric_keys)
        series = [s for s in series if s.key in wanted]
    if not series:  # requested keys matched nothing → fall back to all
        series = list(default_delta.series)
    default_at = {s.key: s.points[h_idx].delta for s in series}

    # --- Sweep each assumption to its low/high edge (others default). ---
    # metric key -> assumption name -> (delta_low, delta_high)
    swept: dict[str, dict[str, tuple[float, float]]] = {s.key: {} for s in series}
    for a in ASSUMPTIONS:
        bp_lo, sp_lo = _apply(base_params, sim_params, {a.name: a.low})
        bp_hi, sp_hi = _apply(base_params, sim_params, {a.name: a.high})
        lo_at = _delta_at(_full_delta(policy, bp_lo, sp_lo, trend), h_idx)
        hi_at = _delta_at(_full_delta(policy, bp_hi, sp_hi, trend), h_idx)
        for s in series:
            swept[s.key][a.name] = (lo_at.get(s.key, 0.0), hi_at.get(s.key, 0.0))

    # --- Per-metric tornado + per-metric influence shares. ---
    tornados: list[MetricTornado] = []
    # (metric key -> assumption name -> influence_share) for the global rollup.
    share_by_metric: dict[str, dict[str, float]] = {}
    for s in series:
        d_def = default_at[s.key]
        raw: list[tuple[str, float, float, float]] = []  # name, d_lo, d_hi, abs_swing
        for a in ASSUMPTIONS:
            d_lo, d_hi = swept[s.key][a.name]
            raw.append((a.name, d_lo, d_hi, abs(d_hi - d_lo)))
        total_abs = sum(r[3] for r in raw)
        shares = {name: (abs_s / total_abs if total_abs > _EPS else 0.0) for name, _, _, abs_s in raw}
        share_by_metric[s.key] = shares

        bars: list[AssumptionSwing] = []
        a_by_name = {a.name: a for a in ASSUMPTIONS}
        for name, d_lo, d_hi, abs_s in raw:
            a = a_by_name[name]
            swing = d_hi - d_lo
            direction = "up" if swing > _EPS else ("down" if swing < -_EPS else "flat")
            bars.append(
                AssumptionSwing(
                    name=name,
                    label=a.label,
                    unit=a.unit,
                    low_value=float(a.low),
                    high_value=float(a.high),
                    delta_at_low=round(d_lo, 4),
                    delta_at_high=round(d_hi, 4),
                    swing=round(swing, 4),
                    abs_swing=round(abs_s, 4),
                    pct_of_default=(round(abs_s / abs(d_def) * 100.0, 2) if abs(d_def) > _EPS else None),
                    influence_share=round(shares[name], 4),
                    direction=direction,
                )
            )
        bars.sort(key=lambda b: b.abs_swing, reverse=True)
        most = bars[0].name if bars and bars[0].abs_swing > _EPS else None
        tornados.append(
            MetricTornado(
                key=s.key,
                label=s.label,
                unit=s.unit,
                tag=s.tag,
                default_delta=round(d_def, 4),
                total_abs_swing=round(total_abs, 4),
                most_influential=most,
                bars=bars,
            )
        )

    # --- Global driver rollup: mean influence share across metrics. ---
    n_metrics = max(1, len(series))
    drivers: list[AssumptionDriver] = []
    a_by_name = {a.name: a for a in ASSUMPTIONS}
    for a in ASSUMPTIONS:
        per_metric_share = [share_by_metric[s.key].get(a.name, 0.0) for s in series]
        global_score = sum(per_metric_share) / n_metrics
        # largest |swing| as % of that metric's default Δ, and the metric it moves most.
        max_pct: float | None = None
        top_metric: str | None = None
        best_share = -1.0
        matters = False
        for s in series:
            d_lo, d_hi = swept[s.key][a.name]
            abs_s = abs(d_hi - d_lo)
            if abs_s > _EPS:
                matters = True
            d_def = default_at[s.key]
            if abs(d_def) > _EPS:
                pct = abs_s / abs(d_def) * 100.0
                if max_pct is None or pct > max_pct:
                    max_pct = round(pct, 2)
            sh = share_by_metric[s.key].get(a.name, 0.0)
            if sh > best_share:
                best_share = sh
                top_metric = s.key
        if not matters:
            note = "Flat on every metric for this policy — the answer does not rest on it here."
            top_metric = None
        elif global_score >= 0.30:
            note = "Dominant driver — pin this down first; the dashboard swings most on it."
        elif global_score >= 0.12:
            note = "Material driver — worth tightening its range."
        else:
            note = "Minor leverage on this policy's outcomes."
        drivers.append(
            AssumptionDriver(
                name=a.name,
                label=a.label,
                unit=a.unit,
                global_score=round(global_score, 4),
                max_pct_of_default=max_pct,
                top_metric=top_metric,
                matters=matters,
                note=note,
            )
        )
    drivers.sort(key=lambda d: d.global_score, reverse=True)

    # --- Plain-language headline. ---
    active = [d for d in drivers if d.matters]
    if not active:
        headline = (
            "No swept assumption moves this policy's headline metrics at the "
            f"{horizon_cp.label} horizon — the effect is structural, not assumption-driven."
        )
    else:
        top = active[0]
        share_pct = round(top.global_score * 100.0, 1)
        headline = (
            f"At {horizon_cp.label}, the answer rests most on '{top.label}' "
            f"(~{share_pct}% of dashboard sensitivity"
            + (f", up to {top.max_pct_of_default:g}% of an effect" if top.max_pct_of_default is not None else "")
            + "). Interactions are not captured — see the /uncertainty fan for the joint spread."
        )

    return SensitivityResult(
        policy_id=policy.id,
        horizon=Checkpoint(
            label=horizon_cp.label, t_months=horizon_cp.t_months, t_years=horizon_cp.t_years
        ),
        swept_assumptions=[a.name for a in ASSUMPTIONS],
        drivers=drivers,
        tornados=tornados,
        headline=headline,
        not_modelled=[
            "One-at-a-time only: interactions between assumptions are not captured "
            "(the §24 Monte-Carlo fan on /uncertainty samples them jointly).",
            "Swept to the documented plausible LOW/HIGH edges — bar length is leverage, "
            "not probability; no distribution is assumed over the range.",
            "Uses the same 8 documented assumptions the uncertainty engine sweeps; "
            "structural model form and the Policy DSL itself are held fixed.",
        ],
    )
