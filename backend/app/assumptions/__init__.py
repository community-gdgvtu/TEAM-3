"""Change-assumptions-and-rerun layer (SPEC §34.10).

SPEC §34's tenth guardrail requires that *users can change the model's input
assumptions and re-run*. The uncertainty engine (§24) sweeps those same
assumptions internally and ranks the most-influential one, but nothing let a
user **pin an assumption to a chosen value and re-run the deterministic core**
to see how much it moves the headline. This module closes that loop.

It introduces NO new numeric model (SPEC §34): it re-runs the exact
deterministic World-A/World-B/Δ pipeline `/simulate` uses, with one or more
documented assumptions overridden, and contrasts the result against the
default-assumption run. The overridable catalogue is the *same* ``ASSUMPTIONS``
registry the uncertainty engine sweeps, so the two can never drift.
"""

from __future__ import annotations

from .catalogue import AssumptionCard, list_assumptions
from .service import AssumptionRerunResult, rerun_with_assumptions

__all__ = [
    "AssumptionCard",
    "AssumptionRerunResult",
    "list_assumptions",
    "rerun_with_assumptions",
]
