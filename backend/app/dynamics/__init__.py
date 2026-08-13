"""System Dynamics / recursive-feedback layer (SPEC §7.6 + §19).

A stocks-and-flows engine that closes the loop the rest of the pipeline leaves
open: it lets public opinion feed back into the *policy itself* over time. The
canonical SPEC §19 cascade — charge → mode shift → revenue → capacity, and
negative support → amendment → weaker charge → less revenue → renewed crowding —
is integrated month-by-month over four coupled stocks (charge, transit demand,
transit capacity, support).

Structural magnitudes come from the deterministic agent-based model at the
in-force charge; the temporal coefficients coupling them are documented
assumptions. Deterministic, LLM-free (SPEC §34).
"""

from __future__ import annotations

from .model import build_system_dynamics
from .params import DEFAULT_SD_PARAMS, SystemDynamicsParams
from .schema import (
    FeedbackContrast,
    FeedbackEvent,
    StockPoint,
    SystemDynamicsResult,
)

__all__ = [
    "build_system_dynamics",
    "DEFAULT_SD_PARAMS",
    "SystemDynamicsParams",
    "FeedbackContrast",
    "FeedbackEvent",
    "StockPoint",
    "SystemDynamicsResult",
]
