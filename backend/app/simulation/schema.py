"""Pydantic schemas for the policy simulation (World B) — ROADMAP M3.

World B is the *with-intervention* counterfactual. It reuses the same headline
metric families as the baseline (mode share / traffic / emissions proxy / transit
demand) so a World-B − World-A delta is a like-for-like comparison, and it adds
two audit surfaces the guardrails require:

* :class:`BehaviouralRule` — SPEC §7.5 mandates that every agent-based
  behavioural rule expose its ``source/calibration``, ``parameter``, ``range``
  and ``sensitivity``. These are the levers the policy pulls on the mode-choice
  model, surfaced for the Evidence Drawer (SPEC §26).
* ``levers`` — the concrete numeric values derived from the Policy DSL for this
  particular run, so a human can see exactly how the compiled policy became
  numbers.

Guardrail (SPEC §34): every number here is produced by the deterministic
structural model, never an LLM → tagged :class:`MetricTag.simulated`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Reuse the baseline metric families so World A / World B are directly comparable.
from ..baseline.schema import (
    EmissionsMetrics,
    Metric,
    MetricTag,
    ModeShare,
    TrafficMetrics,
    TransitMetrics,
)


class BehaviouralRule(BaseModel):
    """One behavioural lever the policy applies to the mode-choice model.

    Mirrors the SPEC §7.5 requirement that each agent-based rule carry its
    calibration source, parameter value, plausible range and a sensitivity note.
    """

    name: str = Field(description="Stable key, e.g. 'cordon_charge'.")
    label: str = Field(description="Human-readable name for the Evidence Drawer.")
    parameter: str = Field(description="What is being changed in the model.")
    value: float = Field(description="The numeric value applied this run.")
    unit: str = Field(default="", description="Unit of ``value`` where meaningful.")
    plausible_range: list[float] = Field(
        default_factory=list, description="[low, high] defensible range for the value."
    )
    sensitivity: str = Field(
        default="", description="How outcomes move if the value changes."
    )
    source: str = Field(
        default="",
        description="Where the value came from: policy DSL field or a stated assumption.",
    )
    active: bool = Field(True, description="Whether this lever is engaged this run.")


class WorldBMetrics(BaseModel):
    """Full World-B snapshot (with the compiled policy applied)."""

    world: str = Field("B", description="'B' = with intervention (SPEC §5).")
    provenance: MetricTag = Field(
        MetricTag.simulated,
        description="Produced by the deterministic agent-based model → Simulated.",
    )
    note: str = Field(
        default=(
            "World B recomputed by the same deterministic agent-based mode-choice "
            "model as World A, with the compiled policy applied as explicit "
            "behavioural levers. No LLM produced any number here (SPEC §34)."
        )
    )
    policy_id: str = Field(description="Id of the Policy DSL that produced this run.")
    population_agents: int
    commuters: int
    mode_share: ModeShare
    traffic: TrafficMetrics
    emissions: EmissionsMetrics
    transit: TransitMetrics
    # Cordon accounting used by later revenue/event-ledger work (SPEC §10).
    priced_car_commuters: int = Field(
        0, description="Car commuters into the CBD who pay the charge (non-exempt)."
    )
    daily_priced_entries: int = Field(
        0, description="Charged CBD entries per day (priced commuters × entries/day)."
    )
    metrics: list[Metric] = Field(
        default_factory=list, description="Flat, provenance-tagged headline numbers."
    )
    behavioural_rules: list[BehaviouralRule] = Field(
        default_factory=list, description="Applied policy levers (SPEC §7.5 audit)."
    )
    levers: dict = Field(
        default_factory=dict, description="Derived numeric levers for this run (auditable)."
    )
    params: dict = Field(
        default_factory=dict, description="Simulation assumptions used (auditable)."
    )
