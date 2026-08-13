"""Pydantic schemas for the policy optimiser stub (ROADMAP stretch, SPEC §22).

Works the problem backwards: given an objective + constraints, grid-search a
handful of candidate interventions, simulate each with the deterministic model,
keep the feasible ones and build a Pareto frontier, then label representative
policies (cheapest / most equitable / largest emissions cut / best balanced).

Guardrail (SPEC §34): the outcome metrics come from the same deterministic
simulation + cohort opinion model as every other endpoint (Simulated). The only
non-simulated number is a transparent, documented cost proxy (Estimated) used
for the budget constraint — clearly flagged and never LLM-produced.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class CandidateConfig(BaseModel):
    """The knobs that define one candidate policy."""

    intervention_type: str
    charge_amount: float | None = None
    public_transport_share: float = 0.0
    exempt_low_income: bool = False
    pedestrianised: bool = False


class CandidateMetrics(BaseModel):
    """Outcome metrics for one candidate at the evaluation horizon."""

    emissions_reduction_pct: float = Field(description="↓ commute CO₂ vs baseline (%). Higher is better.")
    traffic_reduction_pct: float = Field(description="↓ CBD-bound car trips vs baseline (%).")
    transit_gain_pct: float = Field(description="↑ peak CBD transit demand vs baseline (%).")
    avg_commute_increase_pct: float = Field(
        description="Size-weighted mean generalized-cost increase across all commuters (%)."
    )
    low_income_burden_pct: float = Field(
        description="Size-weighted mean generalized-cost increase on low-income commuters (%)."
    )
    net_support: float = Field(description="Modelled net public support in [-1, 1].")
    est_cost: float = Field(description="Illustrative scheme cost (Estimated proxy, not simulated).")


class Candidate(BaseModel):
    """One evaluated candidate policy."""

    policy_id: str
    label: str
    description: list[str] = Field(default_factory=list)
    config: CandidateConfig
    metrics: CandidateMetrics
    feasible: bool = Field(description="Satisfies every supplied constraint.")
    violated_constraints: list[str] = Field(default_factory=list)
    pareto: bool = Field(default=False, description="On the feasible Pareto frontier.")


class Recommendations(BaseModel):
    """Representative picks from the frontier (SPEC §22 output)."""

    cheapest: str | None = Field(default=None, description="policy_id — lowest est_cost.")
    most_equitable: str | None = Field(default=None, description="policy_id — lowest low-income burden.")
    largest_emissions_reduction: str | None = Field(default=None, description="policy_id — biggest CO₂ cut.")
    best_balanced: str | None = Field(default=None, description="policy_id — closest to the ideal point.")


class OptimiserResult(BaseModel):
    """Full optimiser payload (SPEC §22)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Objective → search policy space → simulate → Pareto. Outcome metrics "
            "are Simulated (deterministic model + cohort opinion); est_cost is an "
            "Estimated, documented proxy for the budget constraint. No LLM produced "
            "any number (SPEC §22/§34). A stub search over a small candidate grid."
        )
    )
    objective: dict = Field(default_factory=dict, description="Echo of the requested objective.")
    constraints: dict = Field(default_factory=dict, description="Echo of the requested constraints.")
    horizon: Checkpoint = Field(description="Evaluation horizon (fully-adapted long-run state).")
    n_candidates: int
    n_feasible: int
    constraints_satisfiable: bool = Field(
        description="At least one candidate satisfied every constraint."
    )
    pareto_front: list[Candidate] = Field(default_factory=list)
    recommendations: Recommendations
    candidates: list[Candidate] = Field(
        default_factory=list, description="Every evaluated candidate (auditable)."
    )
    cost_model: dict = Field(
        default_factory=dict, description="The Estimated cost-proxy assumptions used."
    )
    objective_axes: list[str] = Field(
        default_factory=list, description="Objectives the Pareto frontier trades off."
    )
