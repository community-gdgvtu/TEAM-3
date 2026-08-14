"""Pydantic schemas for the economic spillover layer (SPEC §7.4)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class SectorExposure(BaseModel):
    """How one economic sector is exposed to the policy (direction + rationale).

    Deliberately an *exposure* record (direction + qualitative magnitude +
    reasoning), not a fabricated hard jobs/GDP number — the sector employment
    response is Estimated and only as good as the elasticities behind it.
    """

    sector: str = Field(description="Economic sector, e.g. 'retail', 'transit_operations'.")
    direction: str = Field(description="'positive' | 'negative' | 'ambiguous'.")
    magnitude: str = Field(description="'low' | 'moderate' | 'high' exposure tier.")
    mechanism: str = Field(description="Why the policy touches this sector.")
    annual_impact_estimate: float | None = Field(
        default=None,
        description="Indicative annual local-currency effect where quantifiable "
        "(None when only a direction can be stated).",
    )
    tag: MetricTag = Field(MetricTag.estimated)


class EconomicChannel(BaseModel):
    """One transparent economic transmission channel (input-output / elasticity).

    Each channel names its mechanism, the Simulated physical quantity it reads,
    the elasticity/IO assumption applied, a central annual monetary estimate with
    a low/high band, its direction and a horizon-decaying confidence. The physical
    driver is Simulated; the monetary translation is Estimated (SPEC §8/§34).
    """

    id: str = Field(description="Stable key, e.g. 'charge_transfer'.")
    name: str = Field(description="Human-readable channel name.")
    mechanism: str = Field(description="One-line causal description.")
    direction: str = Field(description="'positive' | 'negative' | 'ambiguous'.")
    physical_basis: str = Field(
        description="The Simulated quantity this channel reads (e.g. 'annual charge "
        "revenue', 'Δ CBD vehicle trips')."
    )
    physical_value: float | None = Field(
        default=None, description="The Simulated driver value used (auditable)."
    )
    annual_impact: float = Field(
        description="Central annual local-currency effect (sign = direction)."
    )
    annual_impact_low: float = Field(description="Lower edge of the estimate band.")
    annual_impact_high: float = Field(description="Upper edge of the estimate band.")
    unit: str = Field(default="local currency / year")
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_label: str = Field(default="")
    tag: MetricTag = Field(MetricTag.estimated)
    assumptions: list[str] = Field(default_factory=list)
    note: str = Field(default="")


class EconomicSpilloverReport(BaseModel):
    """Local-economy spillover report for one policy run (SPEC §7.4).

    A transparent partial-equilibrium estimate — NOT a GDP figure and NOT a
    Simulated core output. Sums the quantified channels into a net annual local
    economic impact with a wide band, lists sector exposure, and is explicit
    about the effects it does *not* model (SPEC §34 honesty).
    """

    provenance: MetricTag = Field(
        MetricTag.estimated,
        description="Economic translation of Simulated outputs via elasticities → "
        "Estimated (the underlying mode-shift/revenue numbers are Simulated).",
    )
    note: str = Field(
        default=(
            "Transparent input-output / elasticity translation of the deterministic "
            "mode-choice simulation into local-economy channels (SPEC §7.4). Physical "
            "drivers (mode shifts, charge revenue, travel-cost changes) are Simulated; "
            "the monetary translation is Estimated. Partial-equilibrium only — no CGE, "
            "no agglomeration/land-value effects. No LLM produced any number (SPEC §34)."
        )
    )
    policy_id: str
    horizon: Checkpoint
    channels: list[EconomicChannel] = Field(default_factory=list)
    sector_exposure: list[SectorExposure] = Field(default_factory=list)
    net_annual_impact: float = Field(
        description="Sum of quantified channel central estimates (sign = net direction)."
    )
    net_annual_impact_low: float
    net_annual_impact_high: float
    net_confidence: float = Field(ge=0.0, le=1.0)
    unit: str = Field(default="local currency / year")
    not_modelled: list[str] = Field(
        default_factory=list,
        description="Economic effects deliberately left unquantified in this MVP "
        "(honesty surface, SPEC §34).",
    )
    assumptions: dict = Field(
        default_factory=dict, description="Economic-translation assumptions used (auditable)."
    )
    headline: str = Field(description="Plain-language summary of the net effect.")
