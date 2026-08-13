"""Ensemble forecasting for the flagship cordon effect (SPEC §8).

SPEC §7 describes a *hybrid* forecast engine (analogue/causal, time-series,
microsimulation, agent-based, system-dynamics, spatial). SPEC §8 says these
layers should be combined into an **ensemble** whose spread is an honest signal:
when methodologically-different estimators agree, confidence is high; when they
disagree, the band must widen.

This package estimates the flagship outcome — the reduction in vehicle trips
entering the central cordon — with three *independent* methods (structural
agent-based, historical-analogue transfer, reduced-form generalized-cost
elasticity), then pools them into a weighted ensemble with an explicit
disagreement measure. No LLM touches any number (SPEC §34).
"""

from .model import build_ensemble, run_ensemble
from .schema import EnsembleForecast, EnsembleMetric, MethodEstimate

__all__ = [
    "build_ensemble",
    "run_ensemble",
    "EnsembleForecast",
    "EnsembleMetric",
    "MethodEstimate",
]
