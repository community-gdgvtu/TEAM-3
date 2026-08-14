"""Result schema for the System Dynamics / recursive-feedback layer (SPEC §7.6/§19)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class StockPoint(BaseModel):
    """One checkpoint of the coupled stock trajectories."""

    t_months: float
    t_years: float
    #: Effective cordon charge in force this month (currency) — can fall via an
    #: endogenous amendment.
    charge: float
    #: Net public support stock, [-1, 1].
    support: float
    #: Peak CBD-bound transit demand (trips/day) pushed onto transit by the charge.
    transit_demand: float
    #: Peak CBD-bound transit *capacity* (trips/day), a stock funded by revenue.
    transit_capacity: float
    #: demand / capacity. > 1.0 ⇒ over-capacity crowding.
    crowding: float
    #: Cumulative reinvested revenue paid into the capacity programme (currency).
    cumulative_reinvestment: float
    #: Annualised charge revenue at the in-force charge this month (currency/yr).
    annual_revenue: float
    #: Widening confidence for this checkpoint (SPEC §9/§24).
    confidence: float


class FeedbackEvent(BaseModel):
    """A discrete second-order event the recursive loop produced (SPEC §10/§19)."""

    t_months: float
    type: str = Field(description="amendment | capacity_exceeded | crowding_relieved | support_recovered")
    label: str
    #: Ordered causal chain, e.g. the SPEC §19 charge→revenue→crowding cascade.
    cause_chain: list[str]
    before: dict = Field(default_factory=dict)
    after: dict = Field(default_factory=dict)
    confidence: float


class FeedbackContrast(BaseModel):
    """Closed-loop (political response ON) vs open-loop (OFF) end-state contrast.

    This is the point of SPEC §19: recursive political feedback changes the
    outcome. Both runs use the identical deterministic model; only the endogenous
    amendment rule is toggled.
    """

    metric: str
    closed_loop: float = Field(description="Value with recursive political response ON.")
    open_loop: float = Field(description="Value with the feedback rule OFF.")
    delta: float
    interpretation: str


class SystemDynamicsResult(BaseModel):
    """Full recursive stock-flow feedback simulation for a policy (SPEC §7.6/§19)."""

    provenance: MetricTag = Field(
        MetricTag.simulated,
        description="Deterministic stock-flow integration of ABM anchors → Simulated.",
    )
    note: str = Field(
        default=(
            "Recursive stocks-and-flows feedback loop (SPEC §19). Structural "
            "magnitudes (demand pull, revenue, support) come from the deterministic "
            "agent-based model; the temporal coefficients that couple them are "
            "documented Estimated assumptions. No LLM touches any number (SPEC §34). "
            "Months here are elapsed policy time, not the diffusion layer's rounds."
        )
    )
    policy_id: str
    political_response_enabled: bool
    #: The recursive loop SPEC §19 names as central, instantiated for this policy.
    loop_description: list[str]
    trajectory: list[StockPoint]
    feedback_events: list[FeedbackEvent]
    contrast: list[FeedbackContrast]
    final_state: StockPoint
    amendments_triggered: int
    anchors: dict = Field(
        default_factory=dict,
        description="ABM-derived structural anchors the loop integrates (Simulated).",
    )
    params: dict = Field(default_factory=dict, description="Dynamics assumptions used.")
    not_modelled: list[str] = Field(default_factory=list)
