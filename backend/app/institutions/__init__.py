"""Multi-agent institutional review layer (SPEC §18).

The Model Parliament (SPEC §11) already fields Government, Opposition, Equity,
Economist and Devil's Advocate. SPEC §18 calls for the *institutional* agents
that assess a policy against a specific professional mandate rather than argue a
political stance: a Climate agent, an Implementation agent, a Legal/Constitutional
research agent, and an Auditor. Each reads the same deterministic simulation
evidence (Δ metrics + event ledger + provenance) and returns a structured,
evidence-grounded review with a verdict. Numbers come only from the model; an LLM
never produces one (SPEC §18/§34).
"""

from .review import build_reviews, run_institutional_review
from .schema import (
    Finding,
    InstitutionalReview,
    InstitutionsResponse,
    Verdict,
)

__all__ = [
    "build_reviews",
    "run_institutional_review",
    "InstitutionsResponse",
    "InstitutionalReview",
    "Finding",
    "Verdict",
]
