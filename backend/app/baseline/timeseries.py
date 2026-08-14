"""Project the World-A snapshot across the Time Machine timeline (ROADMAP M2).

The baseline snapshot (:func:`app.baseline.model.compute_baseline`) is a single
no-intervention state. The dashboard/time-machine (SPEC §9) needs the same
metrics as *trajectories* over the default checkpoints so World B deltas (M3)
have a reference curve to sit against.

Guardrails (SPEC §34):

* Every projected number is still :class:`MetricTag.simulated` — it is a
  deterministic transform of the structural snapshot, no LLM involved.
* The baseline is a *reference*, not a forecast of a policy. Volume metrics
  (vehicle-km, CO₂, transit trips …) drift only with a single transparent
  exogenous background-demand trend; mode-share **percentages** stay flat
  because no behaviour changes without a policy.
* The confidence band widens monotonically with the horizon (SPEC §9): a small
  model/measurement uncertainty at T0 growing linearly per year up to a cap.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from .model import cached_baseline
from .schema import (
    BaselineMetrics,
    BaselineTimeSeries,
    Checkpoint,
    MetricPoint,
    MetricSeries,
)

# Default Time Machine milestones (SPEC §9), as (label, months).
_CHECKPOINTS: tuple[tuple[str, float], ...] = (
    ("T0", 0.0),
    ("1 month", 1.0),
    ("3 months", 3.0),
    ("5 months", 5.0),
    ("1 year", 12.0),
    ("2 years", 24.0),
    ("5 years", 60.0),
    ("10 years", 120.0),
)

# Metric keys that are *shares* (percentages), not volumes. Baseline behaviour is
# unchanged without a policy, so these stay flat across the horizon.
_SHARE_KEYS = {
    "mode_share.car_pct",
    "mode_share.public_transit_pct",
    "mode_share.walk_pct",
}


@dataclass(frozen=True)
class BaselineTrend:
    """Transparent assumptions for carrying the snapshot forward in time.

    These are *input assumptions* (auditable via the Evidence Drawer), not LLM
    outputs. They describe the counterfactual "nothing changes" world.
    """

    #: Exogenous background growth applied to volume metrics, compounded yearly
    #: (population/economic drift with no policy). ~1.5%/yr is a mild default.
    demand_growth_per_year: float = 0.015
    #: Relative half-width of the confidence band at T0 (model/measurement noise).
    uncertainty_base: float = 0.03
    #: How fast the band widens, in relative half-width added per year (SPEC §9).
    uncertainty_slope_per_year: float = 0.02
    #: Cap so a 10-year band stays interpretable rather than exploding.
    uncertainty_cap: float = 0.30

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_TREND = BaselineTrend()


def _band_rel(years: float, trend: BaselineTrend) -> float:
    """Relative half-width of the uncertainty band at ``years`` (monotone ↑)."""
    return min(
        trend.uncertainty_cap,
        trend.uncertainty_base + trend.uncertainty_slope_per_year * years,
    )


def _project_point(
    base_value: float, years: float, is_share: bool, trend: BaselineTrend
) -> MetricPoint:
    """Project one metric to ``years`` ahead with a widening band."""
    if is_share:
        central = base_value  # shares stay flat in the no-intervention baseline
    else:
        central = base_value * (1.0 + trend.demand_growth_per_year) ** years
    rel = _band_rel(years, trend)
    half = abs(central) * rel
    return MetricPoint(
        t_months=round(years * 12.0, 3),
        value=round(central, 3),
        low=round(central - half, 3),
        high=round(central + half, 3),
    )


def build_timeseries(
    snapshot: BaselineMetrics | None = None,
    trend: BaselineTrend = DEFAULT_TREND,
) -> BaselineTimeSeries:
    """Build the World-A metric trajectories from a baseline snapshot."""
    snap = snapshot if snapshot is not None else cached_baseline()

    checkpoints = [
        Checkpoint(label=label, t_months=months, t_years=round(months / 12.0, 4))
        for label, months in _CHECKPOINTS
    ]

    series: list[MetricSeries] = []
    for m in snap.metrics:
        is_share = m.key in _SHARE_KEYS
        points = [
            _project_point(m.value, cp.t_years, is_share, trend) for cp in checkpoints
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

    return BaselineTimeSeries(
        checkpoints=checkpoints,
        series=series,
        trend=trend.as_dict(),
    )


@lru_cache(maxsize=1)
def cached_timeseries() -> BaselineTimeSeries:
    """Cached default-assumption baseline time series (dataset is static/run)."""
    return build_timeseries()


def clear_cache() -> None:
    cached_timeseries.cache_clear()
