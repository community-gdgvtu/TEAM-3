"""Baseline World Model composition (SPEC §5 / §28.2).

Composes World A into the six SPEC §5 layers (Population, Economy, Geography,
Environment, Institutions, Society) from the synthetic dataset + the baseline
agent-based model. Structural snapshot, not a forecast; no LLM (SPEC §34).
"""

from .model import ALL_LAYERS, clear_cache, compose_world
from .schema import WorldModel

__all__ = ["ALL_LAYERS", "clear_cache", "compose_world", "WorldModel"]
