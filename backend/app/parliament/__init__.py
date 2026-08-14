"""Model Parliament package (ROADMAP M5, SPEC §11/§12).

An adversarial policy stress test: a panel of personas (Government, Opposition,
Equity advocate, Economist, Devil's Advocate) argue for and against a compiled
policy, each grounding every claim in the deterministic simulation's Δ(B−A)
metrics and the event ledger. The LLM only phrases the speeches; it never
generates a figure (SPEC §34), and a template fallback keeps the endpoint working
with no API key.
"""

from .debate import ask_persona, run_debate, simulate_brief
from .failure_modes import (
    FailureMode,
    FailureModeRegister,
    Severity,
    build_failure_register,
)
from .personas import DebateBrief, PANEL_BY_NAME, build_arguments
from .schema import (
    Argument,
    AskRequest,
    AskResponse,
    DebateRequest,
    DebateResponse,
    EvidenceCitation,
    Stance,
)

__all__ = [
    "run_debate",
    "simulate_brief",
    "ask_persona",
    "DebateBrief",
    "build_arguments",
    "PANEL_BY_NAME",
    "build_failure_register",
    "FailureMode",
    "FailureModeRegister",
    "Severity",
    "Argument",
    "AskRequest",
    "AskResponse",
    "DebateRequest",
    "DebateResponse",
    "EvidenceCitation",
    "Stance",
]
