"""Pydantic schemas for the distributional microsimulation (SPEC §7.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class ConstraintCheck(BaseModel):
    """Whether the policy's own stated equity constraint holds against the numbers.

    A policy may declare ``constraints.max_low_income_burden_increase_pct`` — a cap
    the minister sets on how much the charge is allowed to raise low-income
    households' cost burden. Until now that cap was recorded and asserted in debate
    but never checked against the modelled distributional outcome (SPEC §34: a
    constraint you never test is theatre). This is that test, computed from the same
    deterministic microsim burden numbers.
    """

    name: str = Field(description="The DSL constraint being checked.")
    cap_pct: float = Field(description="The stated maximum low-income burden increase (% of income).")
    modelled_low_income_burden_pct: float = Field(
        description="Modelled World-B out-of-pocket charge burden on the lowest-income "
        "decile as % of income. Baseline burden is zero (no charge), so this IS the "
        "increase the cap governs."
    )
    satisfied: bool = Field(description="Whether the modelled increase is within the stated cap.")
    margin_pct: float = Field(
        description="Cap minus modelled burden: positive = headroom, negative = overshoot."
    )
    note: str = Field(default="", description="Plain-language reading of the check.")
    provenance: MetricTag = Field(MetricTag.simulated)


class GroupImpact(BaseModel):
    """Distributional impact for one population subgroup (SPEC §7.3)."""

    group: str = Field(description="Subgroup label, e.g. 'Decile 1 (lowest income)'.")
    agents: int = Field(description="Sampled commuters in this group.")
    mean_gc_change_min: float = Field(
        description="Mean change in per-trip generalized cost (minutes-equiv). "
        "Positive = worse off, negative = better off."
    )
    mean_money_equiv_daily: float = Field(
        description="Mean daily welfare change in money-equivalent (Estimated, via "
        "the population value-of-time). Positive = a daily loss."
    )
    mean_charge_paid_daily: float = Field(description="Mean out-of-pocket cordon charge paid per day.")
    mean_burden_pct_income: float = Field(
        description="Mean annual charge paid as a % of annual income (0 for non-payers)."
    )
    pct_worse_off: float = Field(description="% of the group with a higher generalized cost.")
    pct_better_off: float = Field(description="% of the group with a lower generalized cost.")
    pct_switched_mode: float = Field(description="% of the group who changed travel mode.")


class MicrosimReport(BaseModel):
    """Full distributional microsimulation report (SPEC §7.3).

    Answers SPEC §7.3's questions directly — *who gains, who loses, by how much,
    which decile, which neighbourhood, which household type* — from the per-agent
    generalized-cost change between World A and World B. Deterministic, no LLM
    (SPEC §34); the welfare change is Simulated, the money-equivalent conversion
    uses a documented Estimated value-of-time.
    """

    policy_id: str
    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Per-agent distributional impact from the change in each commuter's "
            "minimum generalized cost (World B − World A) under the same "
            "deterministic mode-choice model as /simulate. 'Who gains' are commuters "
            "whose best option got cheaper (e.g. reinvested transit); 'who loses' pay "
            "the charge or accept a costlier trip. No LLM produces any number (§34)."
        )
    )
    commuters: int
    winners: int = Field(description="Commuters better off (lower generalized cost).")
    losers: int = Field(description="Commuters worse off (higher generalized cost).")
    unaffected: int
    mean_gc_change_min: float = Field(description="Population mean per-trip generalized-cost change.")
    payers: int = Field(description="Commuters paying the cordon charge under the policy.")
    mean_payer_burden_pct: float = Field(
        description="Mean annual-charge burden (% of income) among charge payers."
    )
    regressivity_ratio: float = Field(
        description="Lowest-decile mean burden ÷ highest-decile mean burden. >1 = "
        "the charge falls harder on lower incomes (regressive); 0 if top decile pays nothing."
    )
    regressivity_note: str = ""
    constraint_check: ConstraintCheck | None = Field(
        default=None,
        description="Compliance of the policy's stated equity constraint against the "
        "modelled low-income burden, when the DSL declares one (else null).",
    )
    by_income_decile: list[GroupImpact] = Field(default_factory=list)
    by_household_type: list[GroupImpact] = Field(default_factory=list)
    by_geography: list[GroupImpact] = Field(default_factory=list)
    by_occupation: list[GroupImpact] = Field(default_factory=list)
    worst_hit: str = Field(default="", description="Named group bearing the largest mean loss.")
    biggest_winner: str = Field(default="", description="Named group with the largest mean gain.")
    params: dict = Field(default_factory=dict, description="Assumptions used (auditable).")
    not_modelled: list[str] = Field(default_factory=list)
