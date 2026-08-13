"""Global one-at-a-time sensitivity ("tornado") layer (SPEC §24/§26).

Answers *"which assumption is the answer resting on?"* across the whole dashboard
by sweeping each documented assumption to its plausible edges and measuring the
swing in every headline metric's policy effect. Deterministic, no LLM (SPEC §34).
"""

from __future__ import annotations

from .schema import (
    AssumptionDriver,
    AssumptionSwing,
    MetricTornado,
    SensitivityResult,
)
from .service import run_sensitivity

__all__ = [
    "AssumptionDriver",
    "AssumptionSwing",
    "MetricTornado",
    "SensitivityResult",
    "run_sensitivity",
]
