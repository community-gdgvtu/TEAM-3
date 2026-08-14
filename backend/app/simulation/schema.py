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
    Checkpoint,
    EmissionsMetrics,
    Metric,
    MetricPoint,
    MetricSeries,
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


class WorldBTimeSeries(BaseModel):
    """World-B metric trajectories across the Time Machine checkpoints (SPEC §9).

    Unlike the baseline (which drifts only with exogenous demand), World B ramps
    from the no-intervention state toward the fully-adapted policy state in two
    transparent, deterministic stages (SPEC §9/§24):

    * **Behavioural substitution (short run)** — commuters re-choose their mode
      almost immediately once the charge/ban lands; this fraction saturates
      within a few months.
    * **Transit capacity ramp (mid run)** — the revenue-funded service uplift is
      planned and built with a lag, so it phases in over the first years and only
      then delivers its full pull onto transit.

    Every point is :class:`MetricTag.simulated` (a deterministic transform of the
    structural anchors — no LLM, SPEC §34). The confidence band widens
    monotonically with the horizon, and is wider than the baseline's because a
    policy response is inherently less certain than "nothing changes".
    """

    world: str = Field("B", description="'B' = with intervention (SPEC §5).")
    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "World-B projection: staged adaptation (short-run behaviour "
            "substitution + mid-run revenue-funded transit ramp) between the "
            "no-intervention baseline and the fully-adapted policy state, with a "
            "horizon-widening confidence band. Deterministic — no LLM (SPEC §34)."
        )
    )
    policy_id: str
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    series: list[MetricSeries] = Field(default_factory=list)
    adaptation: dict = Field(
        default_factory=dict, description="Staged-adaptation assumptions used (auditable)."
    )


class DeltaPoint(BaseModel):
    """World-B − World-A for one metric at one checkpoint, with a combined band."""

    t_months: float
    world_a: float = Field(description="World-A central value at this horizon.")
    world_b: float = Field(description="World-B central value at this horizon.")
    delta: float = Field(description="World-B − World-A (the policy effect).")
    delta_pct: float | None = Field(
        default=None,
        description="Δ as % of the World-A value (None when World A is ~0).",
    )
    low: float = Field(description="Lower edge of the Δ uncertainty band.")
    high: float = Field(description="Upper edge of the Δ uncertainty band.")


class DeltaSeries(BaseModel):
    """One metric's World-B − World-A trajectory across the timeline."""

    key: str
    label: str
    unit: str
    tag: MetricTag = Field(MetricTag.simulated)
    method: str = Field(
        default="World-B central minus World-A central at each checkpoint; band is "
        "the two worlds' bands combined in quadrature."
    )
    points: list[DeltaPoint] = Field(default_factory=list)


class DeltaTimeSeries(BaseModel):
    """Δ(B−A) per metric across the Time Machine checkpoints (SPEC §5/§21)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Policy effect = World B (with intervention) − World A (baseline) at "
            "each checkpoint. Both worlds share the same exogenous background "
            "trend, so the delta isolates the intervention. Simulated (SPEC §34)."
        )
    )
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    series: list[DeltaSeries] = Field(default_factory=list)


class LedgerEvent(BaseModel):
    """One structured simulation event (SPEC §10).

    Events are the *shared truth* other engines (parliament, opinion model, press
    simulation, red team) read — narratives may cite them but must never invent
    quantitative events absent from the ledger. Every field here is derived
    deterministically from the World-A/World-B model output, so the ledger is
    tagged Simulated (SPEC §34).
    """

    id: str = Field(description="Stable event id, e.g. 'ev_transit_capacity'.")
    type: str = Field(description="Event family, e.g. 'transit_capacity'.")
    scenario_month: float = Field(description="Months after implementation it fires.")
    scenario_year: float = Field(description="Same horizon in years.")
    timestamp: str | None = Field(
        default=None,
        description="Calendar date (implementation_date + scenario_month), if known.",
    )
    description: str = Field(description="One-line human-readable summary.")
    cause: list[str] = Field(
        default_factory=list, description="Upstream drivers (policy levers / prior events)."
    )
    affected_agents: int = Field(
        0, description="Commuters/trips materially affected (modelled count)."
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence it occurs — falls with the horizon."
    )
    downstream: list[str] = Field(
        default_factory=list, description="Effects this event propagates into."
    )
    severity: str = Field(
        default="info", description="'info' | 'notable' | 'critical' (magnitude tier)."
    )
    evidence: dict = Field(
        default_factory=dict,
        description="Metric keys + values that triggered the event (Evidence Drawer).",
    )
    provenance: MetricTag = Field(MetricTag.simulated)


class EventLedger(BaseModel):
    """Ordered ledger of simulation events for a policy run (SPEC §10)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Deterministic event ledger derived from the World-A/World-B model. "
            "The shared truth other engines read; narratives may cite these events "
            "but must not invent quantitative events absent here (SPEC §10/§34)."
        )
    )
    policy_id: str
    events: list[LedgerEvent] = Field(default_factory=list)
    thresholds: dict = Field(
        default_factory=dict, description="Detection thresholds used (auditable)."
    )
