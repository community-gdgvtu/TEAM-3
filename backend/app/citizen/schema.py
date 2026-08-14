"""Pydantic schemas for the Citizen View (SPEC §17 Citizen View, §31 Agent State)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CitizenProfile(BaseModel):
    """The static profile of one synthetic household (SPEC §17 "Click a household")."""

    agent_id: str = Field(description="Stable synthetic-agent id, e.g. 'CIT-04821'.")
    age: int
    household_size: int
    income_monthly: float = Field(description="Synthetic monthly income (currency units).")
    income_annual: float = Field(description="Monthly income × 12.")
    income_band: str = Field(description="low | lower-middle | middle | upper-middle | upper.")
    occupation: str
    home_zone: str
    home_in_central_district: bool
    work_zone: str
    commutes_into_cbd: bool = Field(description="Whether this agent commutes into the priced/central district.")
    commute_distance_km: float
    car_access: bool
    public_transit_access: bool
    provenance: str = Field(
        default="Simulated — synthetic micro-agent (SPEC §6); not a real person.",
    )


class CitizenSnapshot(BaseModel):
    """This citizen's experience at one Time-Machine checkpoint (SPEC §17)."""

    label: str = Field(description="Checkpoint label, e.g. 'BEFORE POLICY', '5 months', '2 years'.")
    t_months: float
    mode: str = Field(description="The dominant realized travel mode at this horizon (car/public_transit/walk).")
    commute_minutes_one_way: float = Field(description="One-way commute time (minutes).")
    commute_minutes_low: float
    commute_minutes_high: float
    monthly_transport_cost: float = Field(description="Modelled monthly out-of-pocket transport cost.")
    monthly_transport_cost_low: float
    monthly_transport_cost_high: float
    charge_paid_monthly: float = Field(description="Portion of the monthly cost that is the cordon charge.")
    policy_support: float = Field(description="This agent's latent policy support in [-1, 1] (SPEC §31).")
    stance: str = Field(description="supports | opposes | neutral, from the support score.")


class AgentState(BaseModel):
    """SPEC §31 core data structure — Agent State at one horizon ``t``."""

    agent_id: str
    t: float = Field(description="Horizon in months.")
    location: str = Field(description="Home zone id (SPEC §31 'location').")
    income: float = Field(description="Synthetic monthly income (SPEC §31).")
    commute_minutes: float
    monthly_transport_cost: float
    policy_support: float
    provenance: str = Field(default="Simulated")


class CitizenView(BaseModel):
    """Full Citizen View for one household under a policy (SPEC §17/§31).

    Deterministic and LLM-free (SPEC §34). The commute / cost / support come from
    the *same* deterministic mode-choice model as ``/simulate`` and the same
    per-agent opinion model as ``/public``, staged across the horizon with the
    *same* adaptation curve as the aggregate Time Machine, so a citizen's numbers
    can never disagree with the dashboard beside them.
    """

    policy_id: str
    selector: str = Field(description="How this household was chosen (agent_id / representative / ...).")
    profile: CitizenProfile
    before_policy: CitizenSnapshot = Field(description="World-A (no-intervention) reference (SPEC §17).")
    trajectory: list[CitizenSnapshot] = Field(
        description="The household's experience across the Time-Machine checkpoints (T0 → 10y)."
    )
    agent_states: list[AgentState] = Field(
        description="The SPEC §31 Agent-State record at each checkpoint."
    )
    headline: str = Field(description="One-line human summary of the change for this household.")
    explanation: list[str] = Field(
        description="Deterministic 'Why?' narrative tied to the staged model (SPEC §17)."
    )
    provenance: str = Field(
        default=(
            "Simulated — per-agent generalized-cost model (SPEC §7.3/§17) staged over "
            "the Time Machine (SPEC §9); support from the cohort opinion model "
            "(SPEC §13). No LLM in the numeric path (SPEC §34)."
        ),
    )
    not_modelled: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)


class CitizenSample(BaseModel):
    """A lightweight, policy-independent household card for a UI picker (SPEC §17)."""

    agent_id: str
    label: str
    income_band: str
    occupation: str
    home_zone: str
    commutes_into_cbd: bool
    baseline_mode: str
    provenance: str = Field(default="Simulated — synthetic micro-agent (SPEC §6).")
