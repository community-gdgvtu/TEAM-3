"""Monte-Carlo / sensitivity uncertainty engine (ROADMAP M7, SPEC §24).

Re-runs the deterministic World-A/B/Δ simulation many times with the key
uncertain *input assumptions* perturbed, and summarises the resulting spread of
a target metric's Δ trajectory into a fan of plausible futures (median +
50/80/95% intervals per horizon), a one-at-a-time sensitivity ranking, and a
behavioural-regime ensemble (model disagreement).

The engine adds NO new behaviour to the model — it only varies documented
assumptions and re-runs the same structural code. The LLM is never on the
numeric path (SPEC §34); perturbed outputs stay Simulated.
"""

from __future__ import annotations

import random
from dataclasses import replace

from ..baseline.model import compute_baseline
from ..baseline.params import BaselineParams
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.levers import SimParams
from ..simulation.model import compute_world_b
from ..simulation.schema import DeltaSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .schema import (
    EnsembleVariant,
    HorizonBand,
    Interval,
    ModelDisagreement,
    SensitivityEntry,
    UncertaintyResult,
)


class UncertainAssumption:
    """A documented model assumption with a plausible range to sweep.

    ``target`` names which dataclass the field lives on: 'base' →
    :class:`BaselineParams`, 'sim' → :class:`SimParams`.
    """

    __slots__ = ("name", "label", "target", "field", "default", "low", "high", "unit")

    def __init__(self, name, label, target, field, default, low, high, unit=""):
        self.name = name
        self.label = label
        self.target = target
        self.field = field
        self.default = default
        self.low = low
        self.high = high
        self.unit = unit


# Key uncertain assumptions (elasticity-like drivers), each with a defensible
# plausible range. Defaults mirror BaselineParams / SimParams so the central run
# reproduces the deterministic /simulate headline.
ASSUMPTIONS: list[UncertainAssumption] = [
    UncertainAssumption(
        "money_to_minutes", "Mode-switch elasticity (money→time disutility)",
        "base", "money_to_minutes", 8.0, 5.0, 12.0, "min/unit",
    ),
    UncertainAssumption(
        "reinvest_max_speed_gain", "Transit service (bus-capacity) response",
        "sim", "reinvest_max_speed_gain", 0.15, 0.05, 0.25, "frac",
    ),
    UncertainAssumption(
        "reinvest_max_fare_cut", "Transit fare-cut from reinvestment",
        "sim", "reinvest_max_fare_cut", 0.30, 0.15, 0.45, "frac",
    ),
    UncertainAssumption(
        "car_speed_cbd_kmh", "Central congestion feedback (car CBD speed)",
        "base", "car_speed_cbd_kmh", 18.0, 14.0, 22.0, "km/h",
    ),
    UncertainAssumption(
        "transit_speed_kmh", "Baseline transit effective speed",
        "base", "transit_speed_kmh", 15.0, 12.0, 18.0, "km/h",
    ),
    UncertainAssumption(
        "car_cost_per_km", "Perceived car running cost",
        "base", "car_cost_per_km", 0.25, 0.18, 0.35, "unit/km",
    ),
    UncertainAssumption(
        "transit_fare", "Baseline transit fare",
        "base", "transit_fare", 1.80, 1.40, 2.40, "unit",
    ),
    UncertainAssumption(
        "car_co2_kg_per_km", "Vehicle CO₂ emissions factor",
        "base", "car_co2_kg_per_km", 0.192, 0.150, 0.240, "kg/km",
    ),
]


class MetricNotFound(LookupError):
    """Raised when the requested metric key is not in the simulation output."""

    def __init__(self, key: str, available: list[str]) -> None:
        self.key = key
        self.available = available
        super().__init__(f"Unknown metric key {key!r}. Available: {', '.join(available)}")


def _delta_series(
    policy: PolicyDSL,
    base_params: BaselineParams,
    sim_params: SimParams,
    trend: dict,
    metric_key: str,
) -> DeltaSeries:
    """Run the full A/B/Δ pipeline once and return the metric's Δ series."""
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
    delta = build_delta(base_ts, b_ts)
    for s in delta.series:
        if s.key == metric_key:
            return s
    raise MetricNotFound(metric_key, [s.key for s in delta.series])


def _apply(base_params, sim_params, overrides: dict):
    """Return (BaselineParams, SimParams) with the overrides applied."""
    base_kw = {a.field: overrides[a.name] for a in ASSUMPTIONS if a.target == "base" and a.name in overrides}
    sim_kw = {a.field: overrides[a.name] for a in ASSUMPTIONS if a.target == "sim" and a.name in overrides}
    bp = replace(base_params, **base_kw) if base_kw else base_params
    sp = replace(sim_params, **sim_kw) if sim_kw else sim_params
    return bp, sp


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile (q in [0, 1]) of a sorted list."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 >= len(sorted_vals):
        return sorted_vals[-1]
    return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])


_LEVELS = (50, 80, 95)
_Q = {50: (0.25, 0.75), 80: (0.10, 0.90), 95: (0.025, 0.975)}


def _intervals(values: list[float]) -> list[Interval]:
    sv = sorted(values)
    out = []
    for lvl in _LEVELS:
        lo_q, hi_q = _Q[lvl]
        out.append(Interval(level=lvl, low=round(_percentile(sv, lo_q), 3), high=round(_percentile(sv, hi_q), 3)))
    return out


def run_uncertainty(
    policy: PolicyDSL,
    metric_key: str,
    *,
    shocks: Shocks | None = None,
    horizon_months: float | None = None,
    samples: int = 100,
    seed: int = 12345,
) -> UncertaintyResult:
    """Monte-Carlo + sensitivity + ensemble uncertainty for ``metric_key``."""
    samples = max(20, min(int(samples), 500))
    base_params, trend = apply_shocks(shocks)
    sim_params = SimParams()

    # Central (default) run — establishes checkpoints, labels, and the headline.
    central = _delta_series(policy, base_params, sim_params, trend, metric_key)
    checkpoints = [p.t_months for p in central.points]
    if horizon_months is None:
        h_idx = checkpoints.index(60.0) if 60.0 in checkpoints else len(checkpoints) - 1
    else:
        h_idx = min(range(len(checkpoints)), key=lambda i: abs(checkpoints[i] - horizon_months))
    point_estimate = central.points[h_idx].delta

    # --- Monte Carlo: each sample yields the whole Δ trajectory (fan for free). ---
    rng = random.Random(seed)
    per_checkpoint: list[list[float]] = [[] for _ in checkpoints]
    for _ in range(samples):
        overrides = {a.name: rng.triangular(a.low, a.high, a.default) for a in ASSUMPTIONS}
        bp, sp = _apply(base_params, sim_params, overrides)
        series = _delta_series(policy, bp, sp, trend, metric_key)
        for i, pt in enumerate(series.points):
            per_checkpoint[i].append(pt.delta)

    headline_vals = per_checkpoint[h_idx]
    median = _percentile(sorted(headline_vals), 0.5)
    mean = sum(headline_vals) / len(headline_vals)

    fan = [
        HorizonBand(
            t_months=central.points[i].t_months,
            t_years=round(central.points[i].t_months / 12.0, 3),
            median=round(_percentile(sorted(vals), 0.5), 3),
            intervals=_intervals(vals),
        )
        for i, vals in enumerate(per_checkpoint)
    ]

    # --- One-at-a-time sensitivity at the headline horizon. ---
    sens: list[SensitivityEntry] = []
    for a in ASSUMPTIONS:
        lo_over = {a.name: a.low}
        hi_over = {a.name: a.high}
        bp_lo, sp_lo = _apply(base_params, sim_params, lo_over)
        bp_hi, sp_hi = _apply(base_params, sim_params, hi_over)
        d_lo = _delta_series(policy, bp_lo, sp_lo, trend, metric_key).points[h_idx].delta
        d_hi = _delta_series(policy, bp_hi, sp_hi, trend, metric_key).points[h_idx].delta
        swing = abs(d_hi - d_lo)
        if d_hi - d_lo > 1e-9:
            direction = "up"
        elif d_hi - d_lo < -1e-9:
            direction = "down"
        else:
            direction = "flat"
        sens.append(
            SensitivityEntry(
                rank=0,
                name=a.name,
                label=a.label,
                unit=a.unit,
                low_value=a.low,
                high_value=a.high,
                delta_at_low=round(d_lo, 3),
                delta_at_high=round(d_hi, 3),
                swing=round(swing, 3),
                swing_pct_of_median=(round(swing / abs(median) * 100.0, 2) if abs(median) > 1e-9 else None),
                direction=direction,
            )
        )
    sens.sort(key=lambda e: e.swing, reverse=True)
    for i, e in enumerate(sens, start=1):
        e.rank = i

    # --- Behavioural-regime ensemble (model disagreement). ---
    regimes = {
        "low_response": {
            "money_to_minutes": 5.0, "reinvest_max_speed_gain": 0.05, "reinvest_max_fare_cut": 0.15,
        },
        "central": {},
        "high_response": {
            "money_to_minutes": 12.0, "reinvest_max_speed_gain": 0.25, "reinvest_max_fare_cut": 0.45,
        },
    }
    regime_labels = {
        "low_response": ("Low-response regime", "Weak price sensitivity, modest service uplift."),
        "central": ("Central regime", "Documented default assumptions."),
        "high_response": ("High-response regime", "Strong price sensitivity, ambitious service uplift."),
    }
    variants: list[EnsembleVariant] = []
    for name, over in regimes.items():
        bp, sp = _apply(base_params, sim_params, over)
        d = _delta_series(policy, bp, sp, trend, metric_key).points[h_idx].delta
        lbl, desc = regime_labels[name]
        variants.append(EnsembleVariant(name=name, label=lbl, delta=round(d, 3), description=desc))
    dvals = [v.delta for v in variants]
    disagreement = ModelDisagreement(variants=variants, spread=round(max(dvals) - min(dvals), 3))

    # Rebuild a Checkpoint for the headline horizon.
    from ..baseline.schema import Checkpoint

    hp = central.points[h_idx]
    checkpoint = Checkpoint(
        label=f"{hp.t_months:g}m", t_months=hp.t_months, t_years=round(hp.t_months / 12.0, 3)
    )

    return UncertaintyResult(
        policy_id=policy.id,
        metric_key=metric_key,
        metric_label=central.label,
        unit=central.unit,
        horizon=checkpoint,
        point_estimate=round(point_estimate, 3),
        median=round(median, 3),
        mean=round(mean, 3),
        intervals=_intervals(headline_vals),
        samples=samples,
        seed=seed,
        fan=fan,
        influential_assumptions=sens,
        model_disagreement=disagreement,
        swept_assumptions=[a.name for a in ASSUMPTIONS],
    )
