"""Baseline (World A) digital-twin package (SPEC §5, ROADMAP M2).

Deterministic agent-based mode-choice model over the synthetic population that
produces the no-intervention reference metrics: mode share, traffic, an
emissions proxy and transit demand. No LLM touches the numeric path (SPEC §34).
"""

from .model import cached_baseline, choose_mode, compute_baseline
from .params import DEFAULT_PARAMS, BaselineParams
from .schema import BaselineMetrics, Metric, MetricTag

__all__ = [
    "compute_baseline",
    "cached_baseline",
    "choose_mode",
    "BaselineParams",
    "DEFAULT_PARAMS",
    "BaselineMetrics",
    "Metric",
    "MetricTag",
]
