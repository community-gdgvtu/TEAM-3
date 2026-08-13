"""Deterministic stress-test engine (SPEC §20).

Re-runs the *same* A/B/Δ core as ``POST /simulate`` once per named scenario — the
transparent no-shock baseline plus each requested shock — and compares the
policy's benefit under each shock to its benefit under the baseline. The output
answers SPEC §20 directly: *this policy holds under X and Y but fails under Z.*

No randomness, no LLM (SPEC §20/§34): shocks are documented scenario overrides of
named input assumptions, applied identically to both worlds so Δ(B−A) keeps
isolating the policy.
"""

from __future__ import annotations

from ..baseline.model import compute_baseline
from ..baseline.timeseries import DEFAULT_TREND, build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.model import compute_world_b
from ..simulation.schema import DeltaSeries, DeltaTimeSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .catalogue import SHOCK_CATALOGUE, ShockScenario, catalogue_keys, get_scenario
from .schema import (
    MetricStress,
    ScenarioResult,
    StressReport,
    StressRobustness,
)

# Headline metrics whose policy benefit we track under stress, with the direction
# of a *good* policy effect. These are the flagship cordon-pricing outcomes.
_HEADLINE: tuple[tuple[str, str], ...] = (
    ("traffic.vehicle_trips_into_cbd", "decrease"),
    ("emissions.daily_co2_tonnes", "decrease"),
    ("mode_share.car_pct", "decrease"),
    ("transit.daily_transit_trips", "increase"),
)

_CHECKPOINT_MONTHS = (0.0, 1.0, 3.0, 5.0, 12.0, 24.0, 60.0, 120.0)
_DEFAULT_HORIZON = 60.0

# Verdict thresholds on the fraction of baseline benefit retained under a shock.
_STRENGTHENED = 1.15
_ROBUST = 0.75
_NEUTRALISED = 0.25


def _snap_horizon(months: float | None) -> float:
    if months is None:
        return _DEFAULT_HORIZON
    return min(_CHECKPOINT_MONTHS, key=lambda c: abs(c - months))


def _horizon_label(months: float) -> str:
    if months < 12:
        return f"{int(round(months))} month{'s' if months != 1 else ''}"
    years = months / 12.0
    return f"{years:.0f} year{'s' if round(years) != 1 else ''}"


def _run_delta(policy: PolicyDSL, shocks: Shocks | None) -> DeltaTimeSeries:
    """Run the deterministic A/B/Δ core under a (possibly shocked) context."""
    params, trend = apply_shocks(shocks, trend=DEFAULT_TREND)
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=params, reinvestment=True)
    b_behav = compute_world_b(policy, params=params, reinvestment=False)
    b_ts = build_world_b_timeline(
        policy,
        baseline=base,
        world_b_full=b_full,
        world_b_behaviour=b_behav,
        params=params,
        trend=trend,
    )
    return build_delta(base_ts, b_ts)


def _delta_at(series: DeltaSeries, horizon: float) -> tuple[float, float | None]:
    """Return (delta, delta_pct) at the checkpoint nearest ``horizon``."""
    pt = min(series.points, key=lambda p: abs(p.t_months - horizon))
    return pt.delta, pt.delta_pct


def _confidence(fidelity: str, horizon: float) -> str:
    """Map fidelity × horizon → high/medium/low (uncertainty widens with horizon)."""
    base = {"modelled": "high", "partial": "medium", "proxy": "low"}.get(
        fidelity, "low"
    )
    if horizon >= 60 and base == "high":
        return "medium"  # long-horizon widening (SPEC §24)
    return base


def _metric_verdict(intended: str, db: float, ds: float) -> tuple[str, float | None]:
    """Classify how a metric's benefit survives a shock.

    Returns (verdict, retained_pct). ``retained_pct`` is None when the policy had
    no material benefit on this metric even at baseline.
    """
    sign_good = -1.0 if intended == "decrease" else 1.0
    benefit_base = db * sign_good
    benefit_shock = ds * sign_good

    if benefit_base <= 1e-9:
        # Policy didn't help this metric even without a shock → nothing to stress.
        return "n/a", None

    retained = benefit_shock / benefit_base
    retained_pct = round(100.0 * retained, 1)

    if benefit_shock < 0:
        verdict = "reversed"
    elif retained < _NEUTRALISED:
        verdict = "neutralised"
    elif retained < _ROBUST:
        verdict = "weakened"
    elif retained <= _STRENGTHENED:
        verdict = "robust"
    else:
        verdict = "strengthened"
    return verdict, retained_pct


def _metric_note(label: str, verdict: str, retained_pct: float | None) -> str:
    if verdict == "n/a":
        return f"Policy has no benefit on {label} even at baseline; not stressed."
    if verdict == "reversed":
        return f"Under this shock the policy makes {label} WORSE than baseline."
    if verdict == "neutralised":
        return f"The policy's {label} benefit is all but wiped out ({retained_pct}% retained)."
    if verdict == "weakened":
        return f"The {label} benefit shrinks to {retained_pct}% of its no-shock size."
    if verdict == "strengthened":
        return f"The shock amplifies the {label} benefit ({retained_pct}% of baseline)."
    return f"The {label} benefit holds ({retained_pct}% of its no-shock size)."


# Worst-metric → scenario verdict.
_SEVERITY = {
    "reversed": 4,
    "neutralised": 3,
    "weakened": 2,
    "robust": 1,
    "strengthened": 0,
    "n/a": -1,
}


def _scenario_verdict(metrics: list[MetricStress]) -> str:
    graded = [m.verdict for m in metrics if m.verdict != "n/a"]
    if not graded:
        return "holds"  # nothing to break (policy had no measured benefit)
    worst = max(graded, key=lambda v: _SEVERITY[v])
    if worst in ("reversed", "neutralised"):
        return "fails"
    if worst == "weakened":
        return "degrades"
    return "holds"


def _build_metrics(
    horizon: float,
    baseline_delta: DeltaTimeSeries,
    scenario_delta: DeltaTimeSeries,
) -> list[MetricStress]:
    base_by_key = {s.key: s for s in baseline_delta.series}
    shock_by_key = {s.key: s for s in scenario_delta.series}
    out: list[MetricStress] = []
    for key, intended in _HEADLINE:
        b_series = base_by_key.get(key)
        s_series = shock_by_key.get(key)
        if b_series is None or s_series is None:
            continue
        db, db_pct = _delta_at(b_series, horizon)
        ds, ds_pct = _delta_at(s_series, horizon)
        verdict, retained = _metric_verdict(intended, db, ds)
        out.append(
            MetricStress(
                key=key,
                label=b_series.label,
                unit=b_series.unit,
                intended_direction=intended,
                delta_baseline=round(db, 3),
                delta_baseline_pct=db_pct,
                delta_shocked=round(ds, 3),
                delta_shocked_pct=ds_pct,
                retained_pct=retained,
                verdict=verdict,
                note=_metric_note(b_series.label, verdict, retained),
            )
        )
    return out


def _scenario_summary(scenario: ShockScenario, verdict: str, metrics: list[MetricStress]) -> str:
    broken = [m.label for m in metrics if m.verdict in ("reversed", "neutralised")]
    weakened = [m.label for m in metrics if m.verdict == "weakened"]
    if verdict == "fails" and broken:
        return (
            f"Under {scenario.label.lower()}, the policy FAILS: its benefit on "
            f"{', '.join(broken)} is neutralised or reversed."
        )
    if verdict == "degrades" and weakened:
        return (
            f"Under {scenario.label.lower()}, the policy still helps but its "
            f"benefit on {', '.join(weakened)} materially weakens."
        )
    return f"The policy holds up under {scenario.label.lower()}."


def _resolve_scenarios(keys: list[str] | None) -> list[ShockScenario]:
    if not keys:
        return list(SHOCK_CATALOGUE)
    resolved: list[ShockScenario] = []
    for k in keys:
        sc = get_scenario(k)
        if sc is None:
            raise KeyError(k)
        resolved.append(sc)
    return resolved


def run_stress_test(
    policy: PolicyDSL,
    scenario_keys: list[str] | None = None,
    horizon_months: float | None = None,
) -> StressReport:
    """Stress a policy across the SPEC §20 named shocks.

    Raises ``KeyError`` (with the offending key) if a requested scenario is
    unknown; the router turns that into a 404 listing the valid keys.
    """
    horizon = _snap_horizon(horizon_months)
    scenarios = _resolve_scenarios(scenario_keys)

    # No-shock reference run (the transparent baseline, SPEC §20).
    baseline_delta = _run_delta(policy, None)
    baseline_metrics = _build_metrics(horizon, baseline_delta, baseline_delta)
    baseline_result = ScenarioResult(
        key="baseline",
        label="Baseline (no shock)",
        category="reference",
        fidelity="modelled",
        confidence=_confidence("modelled", horizon),
        caveat="Transparent default context; all shocks are measured against this.",
        overrides={},
        metrics=baseline_metrics,
        verdict="reference",
        summary="The policy's effect under the default, un-shocked world.",
    )

    results: list[ScenarioResult] = []
    robust_to: list[str] = []
    degrades: list[str] = []
    fails: list[str] = []

    for sc in scenarios:
        scenario_delta = _run_delta(policy, sc.overrides)
        metrics = _build_metrics(horizon, baseline_delta, scenario_delta)
        verdict = _scenario_verdict(metrics)
        results.append(
            ScenarioResult(
                key=sc.key,
                label=sc.label,
                category=sc.category,
                fidelity=sc.fidelity,
                confidence=_confidence(sc.fidelity, horizon),
                caveat=sc.caveat,
                overrides=sc.overrides.model_dump(),
                metrics=metrics,
                verdict=verdict,
                summary=_scenario_summary(sc, verdict, metrics),
            )
        )
        if verdict == "fails":
            fails.append(sc.key)
        elif verdict == "degrades":
            degrades.append(sc.key)
        else:
            robust_to.append(sc.key)

    robustness = StressRobustness(
        robust_to=robust_to,
        degrades_under=degrades,
        fails_under=fails,
        headline=_robustness_headline(robust_to, degrades, fails),
    )

    return StressReport(
        policy_id=policy.id,
        horizon_months=horizon,
        horizon_label=_horizon_label(horizon),
        baseline=baseline_result,
        scenarios=results,
        robustness=robustness,
    )


def _robustness_headline(
    robust_to: list[str], degrades: list[str], fails: list[str]
) -> str:
    parts: list[str] = []
    if fails:
        parts.append(f"fails under {len(fails)} scenario(s) ({', '.join(fails)})")
    if degrades:
        parts.append(f"degrades under {len(degrades)} ({', '.join(degrades)})")
    if robust_to:
        parts.append(f"holds under {len(robust_to)} ({', '.join(robust_to)})")
    if not parts:
        return "No scenarios evaluated."
    return "Policy " + "; ".join(parts) + "."


def all_scenario_cards() -> list[dict]:
    """Serialisable catalogue for the GET endpoint."""
    return [s.as_card() for s in SHOCK_CATALOGUE]


__all__ = ["run_stress_test", "all_scenario_cards", "catalogue_keys"]
