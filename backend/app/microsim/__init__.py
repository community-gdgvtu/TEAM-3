"""Distributional microsimulation layer (SPEC §7.3).

Answers, at person level, who gains and who loses under a policy and by how much,
broken down by income decile, household type, home neighbourhood and occupation —
from each commuter's change in minimum generalized cost between World A and World
B. Deterministic, no LLM (SPEC §34).
"""

from .model import build_microsim_report
from .schema import GroupImpact, MicrosimReport

__all__ = ["build_microsim_report", "MicrosimReport", "GroupImpact"]
