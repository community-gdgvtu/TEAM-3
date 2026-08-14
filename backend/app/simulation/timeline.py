"""Project the World-B policy state across the Time Machine timeline (ROADMAP M3).

A single :func:`~app.simulation.model.compute_world_b` snapshot is the *fully
adapted* end-state of a policy. The Time Machine (SPEC §9) needs the policy's
metrics as **trajectories** that ramp in over the standard checkpoints
(T0, 1m, 3m, 5m, 1y, 2y, 5y, 10y), because a real intervention does not deliver
its full effect on day one.

Staged adaptation (SPEC §9/§24), modelled deterministically:

* **Behavioural substitution — short run.** The moment the charge / pedestrian
  ban lands, price-sensitive commuters re-choose their mode. This is captured by
  the *reinvestment-off* World-B anchor and fades in fast (saturating within a
  few months).
* **Transit capacity ramp — mid run.** The revenue-funded fare cut and service
  uplift must be planned, funded and built, so they arrive with a lag and phase
  in over the first years. This is the gap between the reinvestment-off and
  reinvestment-on World-B anchors, faded in slowly.
* On top of both, the same **exogenous background-demand growth** as the baseline
  is applied to volume metrics so World A and World B share one background trend
  and their delta is like-for-like.

Guardrails (SPEC §34):

* Every projected number is a deterministic interpolation of three structural
  anchors (World A, reinvestment-off World B, reinvestment-on World B). No LLM
  touches the numeric path → :class:`MetricTag.simulated`.
* The confidence band widens monotonically with the horizon (SPEC §9) and is
  wider than the baseline's, reflecting that a policy response is less certain
  than "nothing changes" (SPEC §24).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from ..baseline.model import cached_baseline
from ..baseline.schema import BaselineMetrics, Checkpoint, MetricPoint, MetricSeries
from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.timeseries import DEFAULT_TREND, BaselineTrend, _CHECKPOINTS, _SHARE_KEYS
from ..policy.dsl import PolicyDSL
from .levers import DEFAULT_SIM_PARAMS, SimParams
from .model import compute_world_b
from .schema import WorldBMetrics, WorldBTimeSeries


@dataclass(frozen=True)
class AdaptationParams:
    """Transparent staged-adaptation assumptions (auditable via Evidence Drawer).

    These describe *how fast* a policy's effect lands, not *how big* it is (the
    magnitude comes from the structural anchors). All are input assumptions, not
    LLM outputs.
    """

    #: Behavioural substitution time-constant (months). Commuters re-choose mode
    #: quickly once the charge/ban lands; τ≈2mo ⇒ ~78% by 3mo, ~92% by 5mo.
    behaviour_tau_months: float = 2.0
    #: Lag before any revenue-funded transit capacity is delivered (months).
    transit_lag_months: float = 6.0
    #: Transit capacity ramp time-constant after the lag (months). τ≈18mo ⇒ the
    #: revenue-funded uplift is ~half-delivered ~1yr in, near-full by ~5yr.
    transit_tau_months: float = 18.0
    #: Relative half-width of the World-B band at T0 (wider than baseline).
    uncertainty_base: float = 0.05
    #: How fast the band widens per year (SPEC §9), steeper than baseline.
    uncertainty_slope_per_year: float = 0.05
    #: Cap so a 10-year policy band stays interpretable.
    uncertainty_cap: float = 0.45

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_ADAPTATION = AdaptationParams()


def _behaviour_fraction(months: float, ad: AdaptationParams) -> float:
    """Share of behavioural substitution realised by ``months`` (0→1, monotone)."""
    if months <= 0:
        return 0.0
    return 1.0 - math.exp(-months / ad.behaviour_tau_months)


def _transit_fraction(months: float, ad: AdaptationParams) -> float:
    """Share of the revenue-funded transit ramp realised by ``months`` (0→1)."""
    delayed = months - ad.transit_lag_months
    if delayed <= 0:
        return 0.0
    return 1.0 - math.exp(-delayed / ad.transit_tau_months)


def _band_rel(years: float, ad: AdaptationParams) -> float:
    """Relative half-width of the World-B band at ``years`` (monotone ↑, SPEC §9)."""
    return min(
        ad.uncertainty_cap,
        ad.uncertainty_base + ad.uncertainty_slope_per_year * years,
    )


def _project_point(
    a_value: float,
    b_behav_value: float,
    b_full_value: float,
    scale: float,
    months: float,
    is_share: bool,
    ad: AdaptationParams,
    trend: BaselineTrend,
) -> MetricPoint:
    """Interpolate one metric across the two adaptation stages at ``months``.

    ``a_value`` is the World-A (baseline) present-day level, ``b_behav_value`` the
    behaviour-only World-B level (transit reinvestment off) and ``b_full_value``
    the fully-adapted World-B level. Behavioural substitution moves A → B_behav;
    the transit ramp then moves B_behav → B_full.

    The band half-width is ``rel(t)`` times a **fixed** per-metric ``scale`` (the
    metric's operating range, not the moving central value) so that the band
    widens monotonically with the horizon as SPEC §9 requires — even for a metric
    whose central value is falling sharply.
    """
    years = months / 12.0
    fb = _behaviour_fraction(months, ad)
    ft = _transit_fraction(months, ad)
    central = a_value + fb * (b_behav_value - a_value) + ft * (b_full_value - b_behav_value)
    if not is_share:
        # Same exogenous background-demand trend as the baseline reference.
        central *= (1.0 + trend.demand_growth_per_year) ** years
    rel = _band_rel(years, ad)
    half = abs(scale) * rel
    return MetricPoint(
        t_months=round(months, 3),
        value=round(central, 3),
        low=round(central - half, 3),
        high=round(central + half, 3),
    )


def build_world_b_timeline(
    policy: PolicyDSL,
    *,
    baseline: BaselineMetrics | None = None,
    world_b_full: WorldBMetrics | None = None,
    world_b_behaviour: WorldBMetrics | None = None,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
    adaptation: AdaptationParams = DEFAULT_ADAPTATION,
    trend: BaselineTrend = DEFAULT_TREND,
) -> WorldBTimeSeries:
    """Build the World-B metric trajectories for ``policy`` across the timeline.

    The three structural anchors can be passed in (so callers that already
    computed them — e.g. ``POST /simulate`` — avoid recomputing) or are derived
    here. The result mirrors the baseline time series so the frontend can overlay
    World A and World B on one Time Machine axis.
    """
    base = baseline if baseline is not None else cached_baseline()
    b_full = (
        world_b_full
        if world_b_full is not None
        else compute_world_b(policy, params=params, sim=sim, reinvestment=True)
    )
    b_behav = (
        world_b_behaviour
        if world_b_behaviour is not None
        else compute_world_b(policy, params=params, sim=sim, reinvestment=False)
    )

    a_by_key = {m.key: m.value for m in base.metrics}
    behav_by_key = {m.key: m.value for m in b_behav.metrics}

    checkpoints = [
        Checkpoint(label=label, t_months=months, t_years=round(months / 12.0, 4))
        for label, months in _CHECKPOINTS
    ]

    series: list[MetricSeries] = []
    for m in b_full.metrics:
        is_share = m.key in _SHARE_KEYS
        a_val = a_by_key.get(m.key, m.value)
        behav_val = behav_by_key.get(m.key, m.value)
        # Fixed per-metric scale for the band: the widest structural level the
        # metric takes across the two worlds, grown to the horizon for volumes so
        # the long-run band stays proportionate. Constant across checkpoints ⇒
        # monotone widening (SPEC §9).
        long_run_growth = (
            1.0 if is_share else (1.0 + trend.demand_growth_per_year) ** (checkpoints[-1].t_years)
        )
        scale = max(abs(a_val), abs(behav_val), abs(m.value)) * long_run_growth
        points = [
            _project_point(
                a_val, behav_val, m.value, scale, cp.t_months, is_share, adaptation, trend
            )
            for cp in checkpoints
        ]
        series.append(
            MetricSeries(
                key=m.key,
                label=m.label,
                unit=m.unit,
                tag=m.tag,
                method=m.method,
                assumptions=m.assumptions,
                points=points,
            )
        )

    return WorldBTimeSeries(
        policy_id=policy.id,
        checkpoints=checkpoints,
        series=series,
        adaptation={**adaptation.as_dict(), "demand_growth_per_year": trend.demand_growth_per_year},
    )
