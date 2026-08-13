"""Model Parliament package (ROADMAP M5, SPEC §11/§12).

An adversarial policy stress test: a panel of personas (Government, Opposition,
Equity advocate, Economist, Devil's Advocate) argue for and against a compiled
policy, each grounding every claim in the deterministic simulation's Δ(B−A)
metrics and the event ledger. The LLM only phrases the speeches; it never
generates a figure (SPEC §34), and a template fallback keeps the endpoint working
with no API key.
"""

from .debate import run_debate
from .personas import DebateBrief, build_arguments
from .schema import (
    Argument,
    DebateRequest,
    DebateResponse,
    EvidenceCitation,
    Stance,
)

__all__ = [
    "run_debate",
    "DebateBrief",
    "build_arguments",
    "Argument",
    "DebateRequest",
    "DebateResponse",
    "EvidenceCitation",
    "Stance",
]
