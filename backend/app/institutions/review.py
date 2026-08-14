"""The four institutional agents (SPEC §18): Climate, Implementation, Legal, Auditor.

Each reads the same deterministic :class:`DebateBrief` the parliament uses (Δ
metrics + event ledger) and returns a structured, evidence-grounded review with a
professional verdict. Verdicts and every cited figure are computed here from the
model — no LLM is involved (SPEC §18/§34).
"""

from __future__ import annotations

from ..parliament.debate import simulate_brief
from ..parliament.personas import DebateBrief
from ..parliament.schema import EvidenceCitation
from ..policy.dsl import InterventionType, PolicyDSL
from ..simulation.schema import LedgerEvent
from ..simulation.shocks import Shocks
from .schema import (
    Finding,
    InstitutionalReview,
    InstitutionsResponse,
    Verdict,
    worst,
)


def _metric_cite(brief: DebateBrief, key: str) -> EvidenceCitation | None:
    d = brief.end.get(key)
    if d is None:
        return None
    pct = f" ({d['delta_pct']:+.0f}%)" if d["delta_pct"] is not None else ""
    return EvidenceCitation(
        kind="metric", ref=key, detail=f"{d['label']}: {d['world_a']} → {d['world_b']} {d['unit']}{pct}"
    )


def _event_cite(ev: LedgerEvent) -> EvidenceCitation:
    return EvidenceCitation(
        kind="event", ref=ev.id,
        detail=f"{ev.description} (month {ev.scenario_month:g}, conf {ev.confidence})",
    )


# --------------------------------------------------------------------------- #
# Climate Agent
# --------------------------------------------------------------------------- #
def climate_agent(brief: DebateBrief) -> InstitutionalReview:
    findings: list[Finding] = []
    cites: list[EvidenceCitation] = []
    emis = brief.end.get("emissions.daily_co2_tonnes")
    ev = brief.event("emissions")
    verdict = Verdict.concern
    if emis and emis["delta"] < 0:
        pct = abs(emis["delta_pct"] or 0.0)
        findings.append(Finding(
            dimension="Transport CO₂",
            detail=(
                f"Daily commuter CO₂ falls from {emis['world_a']} to {emis['world_b']} "
                f"tonnes ({emis['delta_pct']:+.0f}%)."
            ),
            severity="info",
        ))
        c = _metric_cite(brief, "emissions.daily_co2_tonnes")
        if c:
            cites.append(c)
        if ev:
            cites.append(_event_cite(ev))
        verdict = Verdict.clear if pct >= 10.0 else Verdict.conditional
        summary = (
            "Directionally aligned with decarbonisation; the reduction is material."
            if verdict == Verdict.clear
            else "Emissions move the right way but the cut is modest — not yet decisive."
        )
        rec = (
            "Bank the cut, but pair with a stated pathway (zone expansion / charge "
            "escalation) so it compounds rather than plateaus."
        )
    else:
        findings.append(Finding(
            dimension="Transport CO₂",
            detail="No modelled reduction in commuter CO₂ from this intervention.",
            severity="risk",
        ))
        summary = "No measurable climate benefit on the current design."
        rec = "Add a lever that shifts trips off private cars, or reallocate revenue to transit."
    findings.append(Finding(
        dimension="Rebound risk",
        detail=(
            "Freed road space can induce latent car demand over time; monitor that the "
            "cut is not eroded as congestion eases."
        ),
        severity="watch",
    ))
    return InstitutionalReview(
        agent="Climate Agent",
        mandate="Alignment of the policy with transport decarbonisation and air quality.",
        verdict=verdict,
        summary=summary,
        findings=findings,
        recommendation=rec,
        citations=cites,
        confidence=0.7,
    )


# --------------------------------------------------------------------------- #
# Implementation Agent
# --------------------------------------------------------------------------- #
def implementation_agent(brief: DebateBrief) -> InstitutionalReview:
    findings: list[Finding] = []
    cites: list[EvidenceCitation] = []
    cap = brief.event("transit_capacity")
    reinv = brief.event("transit_reinvestment")
    verdict = Verdict.clear
    summary = "Deliverable on the modelled timeline with routine operational planning."
    rec = "Proceed; keep transit reliability under active monitoring."

    if cap and reinv and cap.scenario_month < reinv.scenario_month:
        verdict = Verdict.concern
        findings.append(Finding(
            dimension="Adaptation gap",
            detail=(
                f"Transit demand exceeds capacity at month {cap.scenario_month:g}, but the "
                f"revenue-funded uplift only lands at month {reinv.scenario_month:g} — riders "
                f"get the worst service exactly when goodwill is thinnest."
            ),
            severity="risk",
        ))
        cites.extend([_event_cite(cap), _event_cite(reinv)])
        summary = "Sequencing risk: crowding precedes the funded capacity uplift."
        rec = (
            "Front-load interim capacity (bus hire / frequency) before charging begins, "
            "or phase the charge in behind delivered service."
        )
    elif cap:
        verdict = Verdict.conditional
        findings.append(Finding(
            dimension="Capacity",
            detail=f"{cap.description}",
            severity="watch",
        ))
        cites.append(_event_cite(cap))
        summary = "Feasible, but transit capacity is the binding constraint to manage."
        rec = "Confirm the capacity ramp is funded and procured before go-live."

    if brief.policy.intervention.type == InterventionType.pedestrianisation:
        findings.append(Finding(
            dimension="Access management",
            detail=(
                "A car ban requires deliveries, emergency access and blue-badge holders "
                "to be actively managed (permits, time windows, enforcement)."
            ),
            severity="watch",
        ))
        if verdict == Verdict.clear:
            verdict = Verdict.conditional

    return InstitutionalReview(
        agent="Implementation Agent",
        mandate="Operational deliverability, sequencing and enforcement.",
        verdict=verdict,
        summary=summary,
        findings=findings,
        recommendation=rec,
        citations=cites,
        confidence=0.65,
    )


# --------------------------------------------------------------------------- #
# Legal / Constitutional Research Agent
# --------------------------------------------------------------------------- #
def legal_agent(brief: DebateBrief) -> InstitutionalReview:
    findings: list[Finding] = []
    cites: list[EvidenceCitation] = []
    verdict = Verdict.conditional
    itype = brief.policy.intervention.type

    if brief.charge > 0:
        findings.append(Finding(
            dimension="Legal base / vires",
            detail=(
                f"A {brief.charge:g} {brief.currency} daily charge must rest on an explicit "
                "statutory power to levy it and to hypothecate the revenue; a charge without "
                "a clear legal base is the most common ground for challenge."
            ),
            severity="risk",
        ))
        findings.append(Finding(
            dimension="Proportionality",
            detail=(
                "The charge level must be shown proportionate to the congestion/air-quality "
                "aim it pursues, with evidence on the record."
            ),
            severity="watch",
        ))

    if brief.charge > 0 and not brief.has_low_income_exemption:
        verdict = Verdict.concern
        findings.append(Finding(
            dimension="Equality / non-discrimination",
            detail=(
                "A flat charge with no low-income or resident exemption raises an "
                "indirect-discrimination and proportionality risk that should be assessed "
                "and documented before adoption."
            ),
            severity="risk",
        ))
        cites.append(EvidenceCitation(
            kind="metric", ref="policy.exemptions",
            detail=f"exemptions = {brief.policy.exemptions or 'none'}",
        ))
    elif brief.has_low_income_exemption:
        findings.append(Finding(
            dimension="Equality / non-discrimination",
            detail="An exemption is present, which materially reduces the discrimination risk.",
            severity="info",
        ))
        cites.append(EvidenceCitation(
            kind="metric", ref="policy.exemptions",
            detail=f"exemptions = {brief.policy.exemptions}",
        ))

    if itype == InterventionType.pedestrianisation:
        findings.append(Finding(
            dimension="Access rights",
            detail=(
                "Removing car access engages rights of access for residents, disabled "
                "drivers and businesses; statutory consultation and reasonable-adjustment "
                "duties must be met."
            ),
            severity="watch",
        ))

    summary = {
        Verdict.concern: "Legally deliverable but carries an equality risk to resolve first.",
        Verdict.conditional: "Legally deliverable subject to a clear legal base and proportionality record.",
    }[verdict]
    rec = (
        "Commission an equality impact assessment and confirm the statutory power and "
        "consultation route before adoption."
    )
    return InstitutionalReview(
        agent="Legal/Constitutional Research Agent",
        mandate="Legal base, proportionality, equality duties and consultation.",
        verdict=verdict,
        summary=summary,
        findings=findings,
        recommendation=rec,
        citations=cites,
        confidence=0.55,
    )


# --------------------------------------------------------------------------- #
# Auditor
# --------------------------------------------------------------------------- #
def auditor_agent(brief: DebateBrief) -> InstitutionalReview:
    """Assesses the *evidence quality* of the run itself (SPEC §18/§26/§34)."""
    findings: list[Finding] = []
    cites: list[EvidenceCitation] = []

    metric_count = len(brief.end)
    findings.append(Finding(
        dimension="Provenance completeness",
        detail=(
            f"All {metric_count} headline Δ metrics are model-derived and tagged Simulated; "
            "each traces to the deterministic mode-choice model, not an LLM."
        ),
        severity="info",
    ))
    findings.append(Finding(
        dimension="Uncertainty discipline",
        detail=(
            f"Confidence bands widen monotonically to the {brief.horizon_years:g}-year horizon, "
            "so long-run figures are not presented as precise."
        ),
        severity="info",
    ))
    cites.append(EvidenceCitation(
        kind="metric", ref="uncertainty.horizon_band",
        detail=f"bands widen to the {brief.horizon_years:g}-year horizon (SPEC §9/§24)",
    ))

    event_count = len(brief.ledger.events)
    if event_count:
        findings.append(Finding(
            dimension="Causal audit trail",
            detail=(
                f"{event_count} structured event-ledger records carry cause / affected / "
                "confidence, giving a reconstructable decision trail (SPEC §10)."
            ),
            severity="info",
        ))
    else:
        findings.append(Finding(
            dimension="Causal audit trail",
            detail="No structured events fired — the effect is too small to cross any threshold.",
            severity="watch",
        ))

    # The audit passes on process even when the policy itself is weak.
    verdict = Verdict.clear
    summary = "The evidence base is transparent, tagged and reproducible — fit to decide on."
    rec = (
        "Publish the model registry and evidence traces alongside the decision so the "
        "figures can be independently checked."
    )
    return InstitutionalReview(
        agent="Auditor",
        mandate="Integrity of the evidence: provenance, uncertainty discipline, reproducibility.",
        verdict=verdict,
        summary=summary,
        findings=findings,
        recommendation=rec,
        citations=cites,
        confidence=0.8,
    )


_PANEL = (climate_agent, implementation_agent, legal_agent, auditor_agent)


def _summarise(reviews: list[InstitutionalReview], overall: Verdict) -> str:
    blockers = [r.agent for r in reviews if r.verdict == Verdict.block]
    concerns = [r.agent for r in reviews if r.verdict == Verdict.concern]
    if blockers:
        return f"Overall: BLOCK — unresolved issues from {', '.join(blockers)}."
    if concerns:
        return (
            f"Overall: {overall.value} — proceed only after resolving concerns raised by "
            f"{', '.join(concerns)}."
        )
    if overall == Verdict.conditional:
        return "Overall: conditional — deliverable subject to the stated conditions."
    return "Overall: clear — no institutional agent raised a blocking issue."


def build_reviews(brief: DebateBrief) -> InstitutionsResponse:
    """Run the four institutional agents over the shared brief (SPEC §18)."""
    reviews = [agent(brief) for agent in _PANEL]
    overall = worst([r.verdict for r in reviews])
    tally: dict = {}
    for r in reviews:
        tally[r.verdict.value] = tally.get(r.verdict.value, 0) + 1
    return InstitutionsResponse(
        policy_id=brief.policy.id,
        reviews=reviews,
        overall_verdict=overall,
        verdict_tally=tally,
        summary=_summarise(reviews, overall),
    )


def run_institutional_review(
    policy: PolicyDSL, shocks: Shocks | None = None
) -> InstitutionsResponse:
    """Simulate, then run the institutional review panel."""
    brief = simulate_brief(policy, shocks=shocks)
    return build_reviews(brief)
