"""Build the ensemble forecast for the flagship cordon effect (SPEC §8).

Three independent estimators of the reduction in vehicle trips entering the
central cordon:

1. **Structural agent-based** (SPEC §7.5) — the deterministic World-B mode-choice
   model's own Δ% at the horizon. The workhorse; highest weight.
2. **Historical-analogue transfer** (SPEC §7.1) — a saturating transfer function
   calibrated on real flat-cordon schemes (their reductions asymptote around
   -25/-30% for strong charges), scaled by this policy's per-one-way charge.
3. **Reduced-form elasticity** (SPEC §7.2) — a low out-of-pocket price elasticity
   of cordon car trips applied to the charge as a % of daily car money cost.

They are pooled with documented weights; the band spans their disagreement. All
deterministic, no LLM (SPEC §34).
"""

from __future__ import annotations

from ..baseline.model import compute_baseline
from ..baseline.params import DEFAULT_PARAMS
from ..baseline.schema import BaselineMetrics, Checkpoint, MetricTag
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import InterventionType, PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.levers import derive_levers
from ..simulation.schema import DeltaTimeSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .schema import EnsembleForecast, EnsembleMetric, MethodEstimate

_FLAGSHIP_KEY = "traffic.vehicle_trips_into_cbd"

# Documented ensemble weights (auditable, SPEC §8).
_WEIGHTS = {"structural_abm": 0.50, "historical_analogue": 0.30, "reduced_form": 0.20}

# Analogue transfer calibration (SPEC §7.1). Real strong flat cordons asymptote
# around a ~-30% reduction; the per-one-way charge that delivers half of that.
_ANALOGUE_ASYMPTOTE_PCT = -30.0
_ANALOGUE_HALF_SAT_PER_ONE_WAY = 4.0  # currency units per one-way trip
_ANALOGUE_SPREAD = (0.6, 1.25)  # low/high multipliers across schemes

# Reduced-form: out-of-pocket price elasticity of cordon car trips (small; real
# cordon reductions imply a low elasticity because the charge is large vs fuel).
_RF_ELASTICITY = {"central": 0.09, "low": 0.06, "high": 0.13}
_RF_CAP_PCT = -70.0  # physical floor on a demand reduction


def _clip(pct: float) -> float:
    """Clamp a reduction to the physically valid range [-100%, 0%]."""
    return max(-100.0, min(0.0, pct))


def _pricing(policy: PolicyDSL) -> bool:
    return policy.intervention.type in {
        InterventionType.road_pricing,
        InterventionType.parking_levy,
        InterventionType.low_emission_zone,
    }


def _structural(delta: DeltaTimeSeries, cp_idx: int) -> MethodEstimate:
    central = 0.0
    for s in delta.series:
        if s.key == _FLAGSHIP_KEY and s.points:
            central = s.points[cp_idx].delta_pct or 0.0
            break
    # A structural point estimate carries a modest internal range (±15% relative).
    central = _clip(central)
    lo, hi = _clip(central * 1.15), _clip(central * 0.85)
    return MethodEstimate(
        method_id="structural_abm",
        name="Structural agent-based model",
        spec_layer="Agent-Based Layer (SPEC §7.5)",
        approach="Deterministic World-B mode re-choice over the synthetic population.",
        central_pct=round(central, 2),
        low_pct=round(min(lo, hi), 2),
        high_pct=round(max(lo, hi), 2),
        weight=_WEIGHTS["structural_abm"],
        applicable=True,
        tag=MetricTag.simulated,
        assumptions=["Generalized-cost mode choice", "Per-agent price sensitivity"],
        note="Internal ±15% range reflects behavioural-parameter uncertainty.",
    )


def _analogue(policy: PolicyDSL) -> MethodEstimate:
    applicable = _pricing(policy)
    charge_one_way = 0.0
    if applicable:
        levers = derive_levers(policy)
        charge_one_way = levers.charge_per_one_way
    # Michaelis–Menten saturation toward the empirical asymptote.
    saturate = (
        charge_one_way / (charge_one_way + _ANALOGUE_HALF_SAT_PER_ONE_WAY)
        if charge_one_way > 0
        else 0.0
    )
    central = _clip(_ANALOGUE_ASYMPTOTE_PCT * saturate)
    lo = _clip(central * _ANALOGUE_SPREAD[1])  # more negative
    hi = _clip(central * _ANALOGUE_SPREAD[0])  # less negative
    return MethodEstimate(
        method_id="historical_analogue",
        name="Historical-analogue transfer",
        spec_layer="Historical Analogue / Causal Layer (SPEC §7.1)",
        approach=(
            "Saturating transfer function calibrated on real flat-cordon schemes "
            "(London/Stockholm/Milan), scaled by this policy's per-one-way charge."
        ),
        central_pct=round(central, 2),
        low_pct=round(min(lo, hi), 2),
        high_pct=round(max(lo, hi), 2),
        weight=_WEIGHTS["historical_analogue"],
        applicable=applicable,
        tag=MetricTag.estimated,
        assumptions=[
            f"Empirical asymptote ≈ {_ANALOGUE_ASYMPTOTE_PCT:.0f}% for strong cordons (Observed, illustrative)",
            f"Half-saturation ≈ {_ANALOGUE_HALF_SAT_PER_ONE_WAY} per one-way trip",
            "Real reductions vary ~0.6–1.25× across schemes",
        ],
        note=(
            "External schemes are illustrative transfer anchors, not this city's "
            "data. Not applicable to a pure car ban."
            if not applicable
            else "External schemes are illustrative transfer anchors, not this city's data."
        ),
    )


def _reduced_form(policy: PolicyDSL, base: BaselineMetrics) -> MethodEstimate:
    applicable = _pricing(policy) and (policy.intervention.amount or 0) > 0
    charge_per_day = float(policy.intervention.amount or 0.0)
    # Representative daily car money cost (round trip) from the baseline snapshot.
    trips = max(1, base.traffic.daily_vehicle_trips)
    km_per_trip = base.traffic.daily_vehicle_km / trips
    daily_car_money = (
        km_per_trip * DEFAULT_PARAMS.trips_per_commuter_per_day * DEFAULT_PARAMS.car_cost_per_km
    )
    price_change_pct = (charge_per_day / daily_car_money * 100.0) if daily_car_money > 0 else 0.0

    def _demand(e: float) -> float:
        return _clip(max(_RF_CAP_PCT, -e * price_change_pct))

    central = _demand(_RF_ELASTICITY["central"]) if applicable else 0.0
    lo = _demand(_RF_ELASTICITY["high"]) if applicable else 0.0
    hi = _demand(_RF_ELASTICITY["low"]) if applicable else 0.0
    return MethodEstimate(
        method_id="reduced_form",
        name="Reduced-form price elasticity",
        spec_layer="Time-Series / Elasticity Layer (SPEC §7.2)",
        approach=(
            "Low out-of-pocket price elasticity of cordon car trips applied to the "
            "charge expressed as a % of daily car money cost."
        ),
        central_pct=round(central, 2),
        low_pct=round(min(lo, hi), 2),
        high_pct=round(max(lo, hi), 2),
        weight=_WEIGHTS["reduced_form"],
        applicable=applicable,
        tag=MetricTag.estimated,
        assumptions=[
            f"Price elasticity ≈ −{_RF_ELASTICITY['central']} (range −{_RF_ELASTICITY['low']}…−{_RF_ELASTICITY['high']})",
            f"Charge ≈ {price_change_pct:.0f}% of representative daily car money cost",
            f"Demand reduction floored at {_RF_CAP_PCT:.0f}%",
        ],
        note="Not applicable to a pure car ban (no charge)." if not applicable else "",
    )


def _disagreement_label(spread: float) -> str:
    if spread < 5.0:
        return "low"
    if spread < 15.0:
        return "moderate"
    return "high"


def _pool(methods: list[MethodEstimate], cp: Checkpoint) -> EnsembleMetric:
    applicable = [m for m in methods if m.applicable]
    if not applicable:
        applicable = methods  # degrade gracefully; never divide by zero
    wsum = sum(m.weight for m in applicable) or 1.0
    central = sum(m.central_pct * m.weight for m in applicable) / wsum
    low = min(m.low_pct for m in applicable)
    high = max(m.high_pct for m in applicable)
    centrals = [m.central_pct for m in applicable]
    spread = max(centrals) - min(centrals)
    label = _disagreement_label(spread)
    if len(applicable) == 1:
        interp = (
            "Only one method applies to this intervention; the band reflects that "
            "single method's own uncertainty, not cross-method agreement."
        )
    elif label == "low":
        interp = "Independent methods largely agree — higher confidence in this magnitude."
    elif label == "moderate":
        interp = "Methods broadly agree on direction with some magnitude spread."
    else:
        interp = "Methods disagree materially — treat the magnitude as genuinely uncertain."
    return EnsembleMetric(
        metric_key=_FLAGSHIP_KEY,
        label="Vehicle trips into the central cordon",
        horizon=cp,
        methods=methods,
        ensemble_central_pct=round(central, 2),
        ensemble_low_pct=round(min(low, high), 2),
        ensemble_high_pct=round(max(low, high), 2),
        method_spread_pct=round(spread, 2),
        disagreement=label,
        interpretation=interp,
    )


def build_ensemble(
    policy: PolicyDSL,
    base: BaselineMetrics,
    delta: DeltaTimeSeries,
    horizon_months: float,
) -> EnsembleForecast:
    """Pool the three methods for the flagship metric at the chosen horizon."""
    cp_idx = max(
        (i for i, cp in enumerate(delta.checkpoints) if cp.t_months <= horizon_months),
        default=len(delta.checkpoints) - 1,
    )
    src = delta.checkpoints[cp_idx]
    cp = Checkpoint(label=src.label, t_months=src.t_months, t_years=src.t_years)

    methods = [
        _structural(delta, cp_idx),
        _analogue(policy),
        _reduced_form(policy, base),
    ]
    metric = _pool(methods, cp)
    return EnsembleForecast(
        policy_id=policy.id,
        horizon=cp,
        metrics=[metric],
        method_weights=dict(_WEIGHTS),
    )


def run_ensemble(
    policy: PolicyDSL, shocks: Shocks | None = None, horizon_months: float = 24.0
) -> EnsembleForecast:
    """Run the sim pipeline, then build the ensemble forecast (SPEC §8)."""
    params, trend = apply_shocks(shocks)
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)
    b_ts = build_world_b_timeline(policy, baseline=base, params=params, trend=trend)
    delta = build_delta(base_ts, b_ts)
    return build_ensemble(policy, base, delta, horizon_months=horizon_months)
