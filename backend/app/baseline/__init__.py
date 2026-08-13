"""Baseline (World A) digital-twin package (SPEC §5, ROADMAP M2).

Deterministic agent-based mode-choice model over the synthetic population that
produces the no-intervention reference metrics: mode share, traffic, an
emissions proxy and transit demand. No LLM touches the numeric path (SPEC §34).
"""

from .model import cached_baseline, choose_mode, compute_baseline
from .params import DEFAULT_PARAMS, BaselineParams
from .schema import BaselineMetrics, BaselineTimeSeries, Metric, MetricTag
from .timeseries import DEFAULT_TREND, BaselineTrend, build_timeseries, cached_timeseries

__all__ = [
    "compute_baseline",
    "cached_baseline",
    "choose_mode",
    "build_timeseries",
    "cached_timeseries",
    "BaselineParams",
    "DEFAULT_PARAMS",
    "BaselineTrend",
    "DEFAULT_TREND",
    "BaselineMetrics",
    "BaselineTimeSeries",
    "Metric",
    "MetricTag",
]
