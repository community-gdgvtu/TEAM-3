"""Policy shortlist ranker (SPEC §21/§22, decision support).

Rank a caller-supplied set of candidate policies head-to-head: simulate each with
the deterministic model, score on a caller-weighted composite + Pareto dominance,
and label the winner / greenest / most-equitable / cheapest / best-balanced picks.
Complements ``/optimise`` (which searches an internal grid) by evaluating *the
caller's own* proposals. No LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from .rank import rank_shortlist
from .schema import (
    NormalizedScores,
    PolicyEntry,
    RankedPolicy,
    ShortlistRecommendations,
    ShortlistRequest,
    ShortlistResult,
    Weights,
)

__all__ = [
    "NormalizedScores",
    "PolicyEntry",
    "RankedPolicy",
    "ShortlistRecommendations",
    "ShortlistRequest",
    "ShortlistResult",
    "Weights",
    "rank_shortlist",
]
