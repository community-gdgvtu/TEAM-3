"""Backtesting harness scaffold (ROADMAP stretch, SPEC §25).

Historical replay of a policy against known outcomes → a scorecard (forecast
error, direction accuracy, interval calibration, event-timing error). Forecast
is Simulated; scores are exact arithmetic; no LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from .harness import example_case, run_backtest
from .schema import (
    ActualEvent,
    ActualObservation,
    EventTimingScore,
    HistoricalCase,
    MetricScore,
    Scorecard,
)

__all__ = [
    "ActualEvent",
    "ActualObservation",
    "EventTimingScore",
    "HistoricalCase",
    "MetricScore",
    "Scorecard",
    "example_case",
    "run_backtest",
]
