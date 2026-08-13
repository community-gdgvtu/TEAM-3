"""Schemas for the policy shortlist ranker (SPEC §21/§22, decision support).

The optimiser (`/optimise`) searches an *internal* candidate grid. This layer
answers the other half of the minister's question: *"here are the proposals
already on my desk — rank them."* The caller supplies 2–8 policies (each an NL
prompt to compile, or a pre-compiled DSL); every one is simulated with the same
deterministic World-B model + cohort opinion model as every other endpoint, then
scored on a transparent weighted composite and a Pareto-dominance analysis.

Guardrail (SPEC §34): every outcome metric is Simulated (deterministic model);
the only non-simulated number is the documented `est_cost` proxy (Estimated),
reused verbatim from the optimiser. No LLM produces any number — the composite
score is an explicit, auditable weighted sum the caller controls.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ..baseline.schema import Checkpoint, MetricTag
from ..optimiser.schema import Candidate
from ..policy.dsl import PolicyDSL


class Weights(BaseModel):
    """Caller-controlled weights for the composite score (each ≥ 0).

    Normalised to sum to 1 before use; all-equal by default. These are the ONLY
    subjective inputs — the underlying metrics are all simulated.
    """

    emissions: float = Field(default=1.0, ge=0.0, description="Weight on emissions cut (higher metric = better).")
    commute: float = Field(default=1.0, ge=0.0, description="Weight on keeping avg commute cost down.")
    equity: float = Field(default=1.0, ge=0.0, description="Weight on keeping low-income burden down.")
    support: float = Field(default=1.0, ge=0.0, description="Weight on net public support.")
    cost: float = Field(default=1.0, ge=0.0, description="Weight on scheme cost (Estimated proxy).")


class PolicyEntry(BaseModel):
    """One item on the shortlist: an NL prompt to compile, or a compiled DSL."""

    label: str | None = Field(default=None, description="Human label (defaults to the derived one).")
    text: str | None = Field(default=None, description="Natural-language policy prompt (compiled by the real compiler).")
    policy: PolicyDSL | None = Field(default=None, description="A pre-compiled Policy DSL.")

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "PolicyEntry":
        if (self.text is None) == (self.policy is None):
            raise ValueError("each shortlist entry needs exactly one of 'text' or 'policy'")
        return self


class ShortlistRequest(BaseModel):
    """Input to ``POST /shortlist``."""

    policies: list[PolicyEntry] = Field(min_length=2, max_length=8, description="2–8 candidate policies to rank.")
    weights: Weights | None = Field(default=None, description="Composite-score weights (all-equal if omitted).")
    objective: dict = Field(default_factory=dict, description="Optional target, e.g. {'reduce_transport_emissions_pct': 8}.")
    constraints: dict = Field(
        default_factory=dict,
        description="Optional hard constraints (max_average_commute_increase_pct, "
        "max_low_income_burden_increase_pct, max_budget).",
    )


class NormalizedScores(BaseModel):
    """Each axis min–max normalised across the shortlist to [0,1] (1 = best here)."""

    emissions: float
    commute: float
    equity: float
    support: float
    cost: float


class RankedPolicy(BaseModel):
    """One evaluated + scored shortlist entry."""

    rank: int = Field(description="1 = best weighted composite among feasible policies.")
    policy_id: str
    label: str
    source: str = Field(description="'compiled_from_text' or 'provided_dsl'.")
    candidate: Candidate = Field(description="Full simulated candidate (config + metrics + feasibility + pareto).")
    normalized: NormalizedScores
    composite_score: float = Field(description="Weighted sum of the normalised axes, in [0,1].")
    notes: list[str] = Field(default_factory=list)


class ShortlistRecommendations(BaseModel):
    """Labelled picks (each a policy_id, or null when the shortlist is empty of feasibles)."""

    winner: str | None = Field(default=None, description="Best weighted composite among feasible policies.")
    greenest: str | None = Field(default=None, description="Largest emissions reduction.")
    most_equitable: str | None = Field(default=None, description="Lowest low-income burden.")
    cheapest: str | None = Field(default=None, description="Lowest est_cost (Estimated proxy).")
    most_supported: str | None = Field(default=None, description="Highest net public support.")
    best_balanced: str | None = Field(default=None, description="Closest to the ideal point (equal-weight, feasible Pareto).")


class ShortlistResult(BaseModel):
    """Full shortlist payload (SPEC §21/§22)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Compile/accept each policy → simulate with the deterministic World-B "
            "model + cohort opinion → normalise each axis across the shortlist → "
            "weighted composite + Pareto dominance. Outcome metrics are Simulated; "
            "est_cost is an Estimated, documented proxy. No LLM produced any number; "
            "the composite weights are the caller's own (SPEC §22/§34)."
        )
    )
    horizon: Checkpoint = Field(description="Evaluation horizon (fully-adapted long-run state).")
    n_policies: int
    n_feasible: int = Field(description="Policies satisfying every supplied constraint.")
    constraints_satisfiable: bool = Field(description="At least one policy feasible.")
    weights: Weights = Field(description="The normalised weights actually applied.")
    objective: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    ranking: list[RankedPolicy] = Field(default_factory=list, description="Sorted best-first (feasible before infeasible).")
    recommendations: ShortlistRecommendations
    per_metric_leaders: dict[str, str] = Field(default_factory=dict, description="axis → leading policy_id.")
    trade_offs: list[str] = Field(default_factory=list, description="Plain-language, number-grounded trade-off notes.")
    cost_model: dict = Field(default_factory=dict, description="The Estimated cost-proxy assumptions used.")
    objective_axes: list[str] = Field(default_factory=list, description="The objectives dominance trades off.")
