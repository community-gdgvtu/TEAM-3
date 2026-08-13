"""Policy amendments + recompute-vs-original (ROADMAP M5, SPEC §12).

The parliament's amendment loop proposes structured, auditable changes to a
compiled policy — exempt the bottom-income commuters, tweak the charge, redirect
revenue to transit — and asks: *what does this change versus the original?* This
module models an :class:`Amendment` as an explicit mutation of the Policy DSL and
computes Δ(amended − original) across the Time Machine checkpoints by reusing the
same deterministic simulation path.

Guardrail (SPEC §34): an amendment only edits the *structured policy*; all numbers
still come from the agent-based model, so both worlds and their delta are
Simulated. Nothing here is LLM-produced.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.model import compute_baseline
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL, RevenueAllocation
from .compare import build_delta
from .model import compute_world_b
from .schema import DeltaTimeSeries, WorldBMetrics
from .shocks import Shocks, apply_shocks
from .timeline import build_world_b_timeline


class Amendment(BaseModel):
    """A structured, auditable change to a compiled policy (SPEC §12)."""

    label: str = Field(
        default="amendment", description="Human name, e.g. 'exempt bottom-30% income'."
    )
    exempt_low_income: bool = Field(
        default=False, description="Add a low-income exemption to the charge."
    )
    exempt_residents: bool = Field(
        default=False, description="Add a resident (in-cordon) exemption."
    )
    set_charge_amount: float | None = Field(
        default=None, description="Override the intervention charge amount."
    )
    charge_multiplier: float | None = Field(
        default=None, gt=0, description="Scale the existing charge amount."
    )
    set_public_transport_share: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override the revenue share reinvested in public transport.",
    )

    def describe(self) -> list[str]:
        """Human-readable list of the concrete changes this amendment makes."""
        out: list[str] = []
        if self.exempt_low_income:
            out.append("exempt low-income commuters from the charge")
        if self.exempt_residents:
            out.append("exempt in-cordon residents from the charge")
        if self.set_charge_amount is not None:
            out.append(f"set the charge to {self.set_charge_amount:g}")
        if self.charge_multiplier is not None:
            out.append(f"scale the charge ×{self.charge_multiplier:g}")
        if self.set_public_transport_share is not None:
            out.append(
                f"reinvest {self.set_public_transport_share:.0%} of revenue in transit"
            )
        return out


def propose_opposition_amendment(
    policy: PolicyDSL,
) -> tuple[Amendment | None, str, str]:
    """Deterministically derive the canonical opposition amendment (SPEC §12/§21).

    This is the structured "World C — Opposition Amendment" of §21: a flat charge
    is regressive, so the first move is to exempt low-income commuters; failing
    that (equity already handled), redirect all revenue into transit. Returns
    ``(amendment | None, source, rationale)``. No LLM — a rule over the DSL shape.
    """
    amount = policy.intervention.amount
    has_charge = amount is not None and amount > 0
    exemptions = [e.lower() for e in policy.exemptions]
    has_low_income = any("income" in e for e in exemptions)
    pt_share = policy.revenue_allocation.public_transport

    if has_charge and not has_low_income:
        return (
            Amendment(label="exempt low-income commuters", exempt_low_income=True),
            "auto:equity",
            "The flat charge is regressive — the lowest-income commuters bear a "
            "disproportionate share of the out-of-pocket burden (SPEC §13). "
            "Exempting them preserves most traffic and climate gains while "
            "improving distributional fairness.",
        )
    if has_charge and pt_share < 0.99:
        return (
            Amendment(
                label="reinvest all revenue in transit", set_public_transport_share=1.0
            ),
            "auto:reinvestment",
            "Directing the full charge revenue into transit funds the capacity "
            "ramp sooner, easing the mid-run crowding the event ledger flags.",
        )
    if not has_charge and pt_share < 0.99:
        return (
            Amendment(
                label="reinvest savings in transit", set_public_transport_share=1.0
            ),
            "auto:reinvestment",
            "With no charge revenue, redirecting the freed budget into transit is "
            "the main lever left to strengthen the transit response.",
        )
    return (
        None,
        "none",
        "The policy already exempts low-income commuters and reinvests fully in "
        "transit; no structural opposition amendment is proposed by default.",
    )


def apply_amendment(policy: PolicyDSL, amendment: Amendment) -> PolicyDSL:
    """Return a new Policy DSL with ``amendment`` applied (original untouched)."""
    amended = policy.model_copy(deep=True)
    amended.id = f"{policy.id}__{amendment.label.replace(' ', '_')}"

    exemptions = list(amended.exemptions)
    if amendment.exempt_low_income and not any("income" in e.lower() for e in exemptions):
        exemptions.append("low-income")
    if amendment.exempt_residents and not any("resident" in e.lower() for e in exemptions):
        exemptions.append("residents")
    amended.exemptions = exemptions

    if amendment.set_charge_amount is not None:
        amended.intervention.amount = amendment.set_charge_amount
    if amendment.charge_multiplier is not None and amended.intervention.amount is not None:
        amended.intervention.amount = round(
            amended.intervention.amount * amendment.charge_multiplier, 4
        )

    if amendment.set_public_transport_share is not None:
        pt = amendment.set_public_transport_share
        amended.revenue_allocation = RevenueAllocation(
            public_transport=pt,
            general_fund=round(1.0 - pt, 4),
        )
    return amended


class AmendmentComparison(BaseModel):
    """Δ(amended − original) plus each policy's own snapshot (SPEC §12/§21)."""

    original_policy_id: str
    amended_policy_id: str
    amendment: Amendment
    changes: list[str] = Field(description="Concrete edits the amendment made.")
    original_world_b: WorldBMetrics
    amended_world_b: WorldBMetrics
    original_vs_baseline: DeltaTimeSeries = Field(
        description="Δ(original − baseline) across checkpoints."
    )
    amended_vs_baseline: DeltaTimeSeries = Field(
        description="Δ(amended − baseline) across checkpoints."
    )
    amendment_delta: DeltaTimeSeries = Field(
        description="Δ(amended − original) — the effect of the amendment itself."
    )


def compare_amendment(
    policy: PolicyDSL,
    amendment: Amendment,
    shocks: Shocks | None = None,
) -> AmendmentComparison:
    """Simulate the original and amended policies and return their comparison."""
    params, trend = apply_shocks(shocks)
    amended_policy = apply_amendment(policy, amendment)

    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)

    orig_b = compute_world_b(policy, params=params, reinvestment=True)
    orig_ts = build_world_b_timeline(policy, baseline=base, params=params, trend=trend)

    amd_b = compute_world_b(amended_policy, params=params, reinvestment=True)
    amd_ts = build_world_b_timeline(amended_policy, baseline=base, params=params, trend=trend)

    return AmendmentComparison(
        original_policy_id=policy.id,
        amended_policy_id=amended_policy.id,
        amendment=amendment,
        changes=amendment.describe(),
        original_world_b=orig_b,
        amended_world_b=amd_b,
        original_vs_baseline=build_delta(base_ts, orig_ts),
        amended_vs_baseline=build_delta(base_ts, amd_ts),
        amendment_delta=build_delta(orig_ts, amd_ts),
    )
