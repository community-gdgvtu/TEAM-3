"""Uncertainty engine (ROADMAP M7, SPEC §24).

Monte-Carlo sweep + one-at-a-time sensitivity + behavioural-regime ensemble over
the deterministic simulation, turning a single policy run into a fan of
plausible futures with ranked most-influential assumptions and model
disagreement. No LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from .engine import ASSUMPTIONS, MetricNotFound, run_uncertainty
from .schema import (
    EnsembleVariant,
    HorizonBand,
    Interval,
    ModelDisagreement,
    SensitivityEntry,
    UncertaintyResult,
)

__all__ = [
    "ASSUMPTIONS",
    "EnsembleVariant",
    "HorizonBand",
    "Interval",
    "MetricNotFound",
    "ModelDisagreement",
    "SensitivityEntry",
    "UncertaintyResult",
    "run_uncertainty",
]
