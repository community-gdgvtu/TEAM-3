"""Schemas for the decision-under-uncertainty layer (SPEC §20 + §21 + §22).

The stress-test layer (SPEC §20) answers *"does **this** policy hold under the
named shocks?"*. This layer answers the decision question one level up:
*"given several candidate policies and a set of possible futures, **which
candidate should a minister actually pick** — the headline winner, or the one
that is least bad when the world turns out otherwise?"*

It is a pure composition of the deterministic stress core over a candidate set —
no new numeric model, no randomness, no LLM (SPEC §34). Every payoff is the same
Simulated Δ(B−A) the stress/simulate endpoints already return.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StateResult(BaseModel):
    """One candidate's outcome in one state of the world (baseline or a shock)."""

    state_key: str = Field(description="'baseline' or a shock key (SPEC §20).")
    state_label: str
    category: str = Field(description="reference | macro | energy | climate | …")
    payoff: float = Field(
        description="Policy benefit on the objective metric in this state "
        "(signed so higher = better outcome). Simulated Δ(B−A) at the horizon."
    )
    payoff_pct: float | None = Field(
        default=None,
        description="Same benefit as a % of the World-A level, where defined.",
    )
    regret: float = Field(
        description="Best candidate's payoff in this state − this candidate's "
        "payoff (≥0). Zero means this candidate is the best choice for this state."
    )
    retained_pct: float | None = Field(
        default=None,
        description="This candidate's benefit here as a % of its own no-shock "
        "benefit (the stress-test 'holds/degrades/fails' basis).",
    )
    confidence: str = Field(description="high | medium | low (widens with horizon).")


class CandidateScore(BaseModel):
    """A candidate policy scored across every state of the world."""

    policy_id: str
    label: str = Field(description="Human-readable candidate label.")
    states: list[StateResult]

    nominal_payoff: float = Field(
        description="Payoff in the baseline (no-shock) state — the 'headline' number."
    )
    worst_case_payoff: float = Field(
        description="Minimum payoff across all states (the maximin criterion input)."
    )
    best_case_payoff: float
    mean_payoff: float = Field(
        description="Mean payoff across states (Laplace / equal-weight criterion)."
    )
    max_regret: float = Field(
        description="Largest regret across states (the minimax-regret criterion input; "
        "Savage). Lower is better."
    )
    robustness_score: float = Field(
        description="Fraction of shock states (0..1) in which the candidate retains "
        "≥75% of its own no-shock benefit — the stress-test 'holds' rate."
    )
    holds_under: list[str] = Field(default_factory=list)
    fails_under: list[str] = Field(default_factory=list)


class DecisionPicks(BaseModel):
    """The candidates each decision criterion selects."""

    nominal_best: str | None = Field(
        default=None, description="Highest baseline payoff — the headline winner."
    )
    maximin: str | None = Field(
        default=None,
        description="Highest worst-case payoff — best if you assume the worst state.",
    )
    minimax_regret: str | None = Field(
        default=None,
        description="Lowest max-regret (Savage) — least 'I wish I'd chosen otherwise'.",
    )
    most_robust: str | None = Field(
        default=None, description="Highest robustness score (holds under most shocks)."
    )
    laplace: str | None = Field(
        default=None, description="Highest mean payoff (equal-weight over states)."
    )


class RobustnessReport(BaseModel):
    """Full decision-under-uncertainty comparison (SPEC §20/§21/§22)."""

    provenance: str = Field(
        default="Simulated",
        description="Every payoff is a deterministic Δ(B−A); no LLM (SPEC §34).",
    )
    objective_key: str
    objective_label: str
    objective_direction: str = Field(description="decrease | increase (a good effect).")
    horizon_months: float
    horizon_label: str
    states: list[str] = Field(description="State keys evaluated (baseline first).")
    candidates: list[CandidateScore]
    picks: DecisionPicks
    headline: str = Field(
        description="One-line decision insight: does robustness change the choice?"
    )
    method: str = Field(
        default=(
            "Payoff = Simulated Δ(B−A) on the objective metric at the horizon, per "
            "candidate × state (baseline + SPEC §20 shocks). Regret is per-state "
            "best-payoff minus candidate payoff. Criteria: nominal, maximin, "
            "minimax-regret (Savage), Laplace, and the stress-test robustness rate. "
            "Deterministic; no LLM touches a number (SPEC §22/§34)."
        )
    )


__all__ = [
    "StateResult",
    "CandidateScore",
    "DecisionPicks",
    "RobustnessReport",
]
