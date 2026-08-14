"""Devil's Advocate → ranked Failure Mode Register (ROADMAP M5, SPEC §12).

Turns the adversarial critique into a structured, ranked register: each failure
mode carries a risk title, the causal mechanism, a severity tier, a probability,
the Simulated evidence it rests on, and a concrete mitigation. Modes are ranked
by expected risk (severity weight × probability).

Guardrail (SPEC §34): the register is an **Estimated** risk overlay — the severity
and probability are transparent structured judgements — but every piece of
*evidence* it cites is a Simulated metric or ledger event. No LLM and no
fabricated metric: a mode is only raised when the model output supports it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag
from .personas import DebateBrief
from .schema import EvidenceCitation


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


_SEVERITY_WEIGHT = {
    Severity.low: 1.0,
    Severity.medium: 2.0,
    Severity.high: 3.0,
    Severity.critical: 4.0,
}


class FailureMode(BaseModel):
    """One ranked entry in the Failure Mode Register (SPEC §12)."""

    id: str
    risk: str = Field(description="Short risk title.")
    mechanism: str = Field(description="How the failure arises.")
    severity: Severity
    probability: float = Field(ge=0.0, le=1.0, description="Estimated likelihood.")
    risk_score: float = Field(description="severity weight × probability (ranking key).")
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    mitigation: str = Field(description="Concrete action that reduces the risk.")
    affected_agents: int = Field(0, description="Commuters/trips exposed, where modelled.")


class FailureModeRegister(BaseModel):
    """Ranked failure modes for a policy run (SPEC §12)."""

    provenance: MetricTag = Field(
        MetricTag.estimated,
        description="Risk scores are Estimated judgements; cited evidence is Simulated.",
    )
    note: str = Field(
        default=(
            "Devil's Advocate register. Severity/probability are transparent "
            "structured estimates; every cited figure is a Simulated metric or "
            "ledger event. Ranked by severity weight × probability (SPEC §12/§34)."
        )
    )
    policy_id: str
    failure_modes: list[FailureMode] = Field(default_factory=list)


def _score(severity: Severity, probability: float) -> float:
    return round(_SEVERITY_WEIGHT[severity] * probability, 3)


def _event_citation(brief: DebateBrief, etype: str) -> tuple[EvidenceCitation | None, object]:
    ev = brief.event(etype)
    if ev is None:
        return None, None
    return (
        EvidenceCitation(
            kind="event",
            ref=ev.id,
            detail=f"{ev.description} (month {ev.scenario_month:g}, conf {ev.confidence})",
        ),
        ev,
    )


def build_failure_register(brief: DebateBrief) -> FailureModeRegister:
    """Derive the ranked Failure Mode Register from a simulation brief."""
    modes: list[FailureMode] = []

    # --- 1. Adaptation gap: crowding before the funded capacity lands -------
    cap_cite, cap = _event_citation(brief, "transit_capacity")
    reinv_cite, reinv = _event_citation(brief, "transit_reinvestment")
    if cap is not None:
        gap = reinv is not None and reinv.scenario_month > cap.scenario_month
        severity = Severity.high if gap else Severity.medium
        # Likelihood tracks the capacity event's own confidence.
        probability = round(min(0.9, 0.5 + 0.4 * cap.confidence), 2)
        cites = [c for c in (cap_cite, reinv_cite) if c is not None]
        mech = (
            f"Behavioural mode shift overwhelms transit at month {cap.scenario_month:g}, "
            + (
                f"but the revenue-funded capacity ramp only lands at month {reinv.scenario_month:g} — "
                "early riders get the worst service."
                if gap
                else "straining the network before service can adjust."
            )
        )
        modes.append(
            FailureMode(
                id="fm_adaptation_gap",
                risk="Transit overcrowding during the adaptation gap",
                mechanism=mech,
                severity=severity,
                probability=probability,
                risk_score=_score(severity, probability),
                evidence=cites,
                mitigation=(
                    "Phase the charge in (or pre-fund bus capacity before day one) so "
                    "service headroom leads demand rather than lagging it."
                ),
                affected_agents=cap.affected_agents,
            )
        )

    # --- 2. Regressive burden → political backlash --------------------------
    if brief.charge > 0 and not brief.has_low_income_exemption:
        severity = Severity.high
        probability = 0.6
        modes.append(
            FailureMode(
                id="fm_regressive_backlash",
                risk="Regressive burden triggers backlash / repeal",
                mechanism=(
                    f"A flat {brief.charge:g} {brief.currency} charge with no low-income or "
                    "resident exemption falls hardest on the least able to pay — the most "
                    "common trigger for public opposition and reversal."
                ),
                severity=severity,
                probability=probability,
                risk_score=_score(severity, probability),
                evidence=[
                    EvidenceCitation(
                        kind="metric",
                        ref="policy.exemptions",
                        detail=f"exemptions = {brief.policy.exemptions or 'none'}",
                    )
                ],
                mitigation=(
                    "Add a low-income / resident exemption (see /simulate/amend) and "
                    "hypothecate revenue visibly to transit before launch."
                ),
                affected_agents=brief.world_b.priced_car_commuters,
            )
        )

    # --- 3. Revenue erosion undermines the funded transit uplift ------------
    ms = brief.end.get("mode_share.car_pct")
    if brief.pt_share > 0 and brief.charge > 0 and ms is not None and ms["delta"] < 0:
        severity = Severity.medium
        probability = 0.5
        modes.append(
            FailureMode(
                id="fm_revenue_erosion",
                risk="Charge revenue erodes as drivers leave",
                mechanism=(
                    f"The same {ms['delta']:+.1f}-pt car-share fall that makes the policy work "
                    "also shrinks the priced base funding the transit uplift, so the mid-run "
                    "reinvestment it depends on is self-limiting."
                ),
                severity=severity,
                probability=probability,
                risk_score=_score(severity, probability),
                evidence=[
                    EvidenceCitation(
                        kind="metric",
                        ref="mode_share.car_pct",
                        detail=f"car share {ms['world_a']}% → {ms['world_b']}% ({ms['delta_pct']:+.0f}%)",
                    )
                ],
                mitigation=(
                    "Plan for a declining revenue path: front-load capacity investment "
                    "and diversify the transit funding base beyond the charge."
                ),
                affected_agents=0,
            )
        )

    # --- 4. Assumption fragility (always present, grows with horizon) -------
    severity = Severity.medium
    probability = round(min(0.7, 0.3 + 0.05 * brief.horizon_years), 2)
    modes.append(
        FailureMode(
            id="fm_assumption_fragility",
            risk="Behavioural-elasticity assumptions may not hold",
            mechanism=(
                f"Every projected benefit is conditional on the assumed price/time "
                f"elasticities and reinvestment pace; the confidence bands widen "
                f"monotonically to the {brief.horizon_years:g}-year horizon precisely "
                "because those inputs are uncertain."
            ),
            severity=severity,
            probability=probability,
            risk_score=_score(severity, probability),
            evidence=[
                EvidenceCitation(
                    kind="metric",
                    ref="uncertainty.horizon_band",
                    detail=f"bands widen to the {brief.horizon_years:g}-year horizon",
                )
            ],
            mitigation=(
                "Run the uncertainty sweep over key elasticities and monitor the "
                "early-months outturn against the modelled path; be ready to retune."
            ),
            affected_agents=0,
        )
    )

    modes.sort(key=lambda m: m.risk_score, reverse=True)
    return FailureModeRegister(policy_id=brief.policy.id, failure_modes=modes)
