"""Evidence / explainability engine (ROADMAP M7, SPEC §26).

Turns any simulated metric into a click-through causal trace
(input-data → transform → model → assumptions → result + confidence) plus the
equations, parameters, historical analogues and citations behind it. Pure
deterministic assembly of existing model output — no LLM on the numeric path
(SPEC §34).
"""

from __future__ import annotations

from .schema import (
    HistoricalAnalogue,
    ProvenanceTrace,
    TraceAssumption,
    TraceConfidence,
    TraceResult,
    TraceStep,
)
from .trace import MetricNotFound, run_evidence

__all__ = [
    "HistoricalAnalogue",
    "MetricNotFound",
    "ProvenanceTrace",
    "TraceAssumption",
    "TraceConfidence",
    "TraceResult",
    "TraceStep",
    "run_evidence",
]
