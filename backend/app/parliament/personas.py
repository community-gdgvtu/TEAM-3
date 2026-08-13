"""Deterministic persona arguments for the Model Parliament (SPEC §11/§12).

Each persona reads the *same* simulation output — the Δ(B−A) trajectory and the
event ledger — and deterministically selects the evidence that fits its role,
building a structured :class:`Argument`. This is the guardrail boundary
(SPEC §34): **which** numbers a persona cites and **what stance** it takes are
computed here from the model, not from an LLM. Only the final prose rendering
(``speech``) may be produced by an LLM, and even then it must preserve these
figures.

Personas: Government (sponsor), Opposition, Equity advocate, Economist, Devil's
Advocate. Together they form the adversarial stress test SPEC §11 asks for.
"""

from __future__ import annotations

from ..baseline.schema import BaselineMetrics
from ..policy.dsl import PolicyDSL
from ..simulation.schema import DeltaTimeSeries, EventLedger, LedgerEvent, WorldBMetrics
from .schema import Argument, EvidenceCitation, Stance


class DebateBrief:
    """Compact, deterministic view of a run's evidence for the personas."""

    def __init__(
        self,
        policy: PolicyDSL,
        world_a: BaselineMetrics,
        world_b: WorldBMetrics,
        delta: DeltaTimeSeries,
        ledger: EventLedger,
    ) -> None:
        self.policy = policy
        self.world_a = world_a
        self.world_b = world_b
        self.ledger = ledger
        # End-state (final checkpoint) delta per metric key.
        self.end: dict[str, dict] = {}
        self.horizon_years = delta.checkpoints[-1].t_years if delta.checkpoints else 0.0
        for s in delta.series:
            if s.points:
                p = s.points[-1]
                self.end[s.key] = {
                    "world_a": p.world_a,
                    "world_b": p.world_b,
                    "delta": p.delta,
                    "delta_pct": p.delta_pct,
                    "label": s.label,
                    "unit": s.unit,
                }
        self.events_by_type: dict[str, LedgerEvent] = {e.type: e for e in ledger.events}

    def event(self, etype: str) -> LedgerEvent | None:
        return self.events_by_type.get(etype)

    # Convenience accessors -------------------------------------------------
    @property
    def charge(self) -> float:
        return float(self.policy.intervention.amount or 0.0)

    @property
    def currency(self) -> str:
        return self.policy.intervention.currency

    @property
    def pt_share(self) -> float:
        return float(self.policy.revenue_allocation.public_transport or 0.0)

    @property
    def exemptions(self) -> list[str]:
        return [e.lower() for e in self.policy.exemptions]

    @property
    def has_low_income_exemption(self) -> bool:
        return any("income" in e or "resident" in e for e in self.exemptions)

    @property
    def daily_revenue(self) -> float:
        # A CBD entrant pays the daily charge once; revenue = priced commuters × amount.
        return round(self.world_b.priced_car_commuters * self.charge, 0)


def _metric_citation(brief: DebateBrief, key: str) -> EvidenceCitation | None:
    d = brief.end.get(key)
    if d is None:
        return None
    pct = f" ({d['delta_pct']:+.0f}%)" if d["delta_pct"] is not None else ""
    return EvidenceCitation(
        kind="metric",
        ref=key,
        detail=f"{d['label']}: {d['world_a']} → {d['world_b']} {d['unit']}{pct}",
    )


def _event_citation(ev: LedgerEvent) -> EvidenceCitation:
    return EvidenceCitation(
        kind="event",
        ref=ev.id,
        detail=f"{ev.description} (month {ev.scenario_month:g}, conf {ev.confidence})",
    )


def _mean_event_conf(events: list[LedgerEvent | None], default: float) -> float:
    vals = [e.confidence for e in events if e is not None]
    return round(sum(vals) / len(vals), 2) if vals else default


def government(brief: DebateBrief) -> Argument:
    points: list[str] = []
    cites: list[EvidenceCitation] = []
    obj = brief.policy.stated_objectives

    cordon = brief.event("cordon_load")
    if cordon:
        points.append(
            f"Congestion is the headline win: {cordon.description}"
        )
        cites.append(_event_citation(cordon))
    ms = brief.end.get("mode_share.car_pct")
    if ms and ms["delta"] < 0:
        points.append(
            f"Car mode share falls from {ms['world_a']}% to {ms['world_b']}% — a "
            f"durable shift to sustainable modes."
        )
        c = _metric_citation(brief, "mode_share.car_pct")
        if c:
            cites.append(c)
    emis = brief.event("emissions")
    if emis:
        points.append(f"On climate, {emis.description}")
        cites.append(_event_citation(emis))
    if brief.pt_share > 0 and brief.daily_revenue > 0:
        points.append(
            f"Every unit of revenue is recycled: ~{brief.daily_revenue:g} "
            f"{brief.currency}/day of charge income funds better buses, so drivers "
            f"who switch get a faster service in return."
        )
        reinv = brief.event("transit_reinvestment")
        if reinv:
            cites.append(_event_citation(reinv))

    if not points:
        points.append(
            "The measure is modest in effect on these assumptions, but moves every "
            "headline metric in the intended direction without adverse surprises."
        )
    headline = "This policy delivers on its stated objectives — the twin proves it."
    conf = _mean_event_conf([cordon, emis], 0.7)
    return Argument(
        persona="Government",
        role="Policy sponsor",
        stance=Stance.support,
        headline=headline,
        points=points,
        citations=cites,
        confidence=conf,
    )


def opposition(brief: DebateBrief) -> Argument:
    points: list[str] = []
    cites: list[EvidenceCitation] = []

    if brief.charge > 0 and brief.world_b.priced_car_commuters > 0:
        points.append(
            f"This is a new tax on {brief.world_b.priced_car_commuters:,} commuters "
            f"who still need to drive in — {brief.charge:g} {brief.currency} a day, "
            f"every working day, whether or not the buses actually improve."
        )
    cap = brief.event("transit_capacity")
    if cap:
        points.append(
            f"The alternative isn't ready: {cap.description} You are pushing people "
            f"onto a network that overflows."
        )
        cites.append(_event_citation(cap))
    ms = brief.end.get("mode_share.car_pct")
    if ms and ms["delta"] < 0:
        points.append(
            f"A {abs(ms['delta']):.1f}-point drop in car use sounds fine in a model, "
            f"but behind it are households and businesses reorganising their lives on "
            f"the strength of assumptions that widen sharply over {brief.horizon_years:g} years."
        )
        c = _metric_citation(brief, "mode_share.car_pct")
        if c:
            cites.append(c)

    if not points:
        points.append(
            "Even on the sponsor's own model the benefits are marginal, yet the "
            "disruption and the charge are entirely real."
        )
    return Argument(
        persona="Opposition",
        role="Main opposition",
        stance=Stance.oppose,
        headline="The costs land on real people before the benefits arrive.",
        points=points,
        citations=cites,
        confidence=_mean_event_conf([cap], 0.6),
    )


def equity(brief: DebateBrief) -> Argument:
    points: list[str] = []
    cites: list[EvidenceCitation] = []
    stance = Stance.conditional

    if brief.charge > 0 and not brief.has_low_income_exemption:
        points.append(
            f"A flat {brief.charge:g} {brief.currency} charge is regressive: it is a "
            f"far larger share of a low-income budget than a high-income one, and the "
            f"DSL carries no low-income or resident exemption."
        )
        cites.append(
            EvidenceCitation(
                kind="metric",
                ref="policy.exemptions",
                detail=f"exemptions = {brief.policy.exemptions or 'none'}",
            )
        )
    elif brief.has_low_income_exemption:
        stance = Stance.support
        points.append(
            "Crucially, the policy already exempts low-income / resident commuters, "
            "which blunts the regressive edge of a flat charge."
        )
        cites.append(
            EvidenceCitation(
                kind="metric",
                ref="policy.exemptions",
                detail=f"exemptions = {brief.policy.exemptions}",
            )
        )

    if brief.pt_share > 0:
        points.append(
            f"Reinvesting {brief.pt_share:.0%} of revenue in public transport is the "
            f"right instinct — the people most exposed to the charge are also the most "
            f"reliant on the buses it funds."
        )
    else:
        points.append(
            "None of the revenue is earmarked for public transport, so the commuters "
            "least able to absorb the charge get nothing back."
        )

    constraint = brief.policy.constraints.max_low_income_burden_increase_pct
    if constraint is not None:
        points.append(
            f"The stated {constraint:g}% cap on low-income burden must be monitored "
            f"against the modelled distributional outcome, not just asserted."
        )

    headline = (
        "Support it — but only with the distributional safeguards in place."
        if stance == Stance.conditional
        else "The fairness safeguards are present; this is a defensible design."
    )
    return Argument(
        persona="Equity Advocate",
        role="Distributional impact",
        stance=stance,
        headline=headline,
        points=points,
        citations=cites,
        confidence=0.65,
    )


def economist(brief: DebateBrief) -> Argument:
    points: list[str] = []
    cites: list[EvidenceCitation] = []

    if brief.daily_revenue > 0:
        annual = round(brief.daily_revenue * brief.world_a.params.get("workdays_per_year", 250))
        points.append(
            f"The charge raises ~{brief.daily_revenue:g} {brief.currency}/day "
            f"(~{annual:,} {brief.currency}/yr at 250 working days) — a real, "
            f"hypothecatable funding stream, not a projection."
        )
    ms = brief.end.get("mode_share.car_pct")
    if ms and ms["delta"] < 0:
        points.append(
            f"The demand response is genuine ({ms['delta']:+.1f} pts of car share), "
            f"which is efficient pricing of a congestion externality — but it also "
            f"erodes the revenue base as drivers leave, a tension to plan for."
        )
        c = _metric_citation(brief, "mode_share.car_pct")
        if c:
            cites.append(c)
    cap = brief.event("transit_capacity")
    if cap:
        points.append(
            f"Watch the sequencing cost: transit demand exceeds capacity around month "
            f"{cap.scenario_month:g}, but the revenue-funded uplift lands later — that "
            f"gap is a deadweight loss in crowding and delay."
        )
        cites.append(_event_citation(cap))

    if not points:
        points.append(
            "With no charge and no revenue, this is a quantity restriction, not a "
            "price instrument — efficient only if the external cost is genuinely high."
        )
    return Argument(
        persona="Economist",
        role="Treasury / finance analyst",
        stance=Stance.conditional,
        headline="Sound pricing logic — mind the revenue base and the sequencing.",
        points=points,
        citations=cites,
        confidence=0.6,
    )


def devils_advocate(brief: DebateBrief) -> Argument:
    points: list[str] = []
    cites: list[EvidenceCitation] = []

    cap = brief.event("transit_capacity")
    reinv = brief.event("transit_reinvestment")
    if cap and reinv and cap.scenario_month < reinv.scenario_month:
        points.append(
            f"Failure mode #1 — the adaptation gap: crowding hits at month "
            f"{cap.scenario_month:g} but the funded capacity only arrives at month "
            f"{reinv.scenario_month:g}. Early riders get the worst service exactly when "
            f"political goodwill is thinnest, risking a reversal before benefits land."
        )
        cites.append(_event_citation(cap))
        cites.append(_event_citation(reinv))
    elif cap:
        points.append(
            f"Failure mode #1 — capacity: {cap.description} If the transit ramp slips, "
            f"this becomes the story of the policy."
        )
        cites.append(_event_citation(cap))

    points.append(
        f"Failure mode #2 — assumption fragility: the {brief.horizon_years:g}-year "
        f"bands widen precisely because behavioural elasticities and the reinvestment "
        f"pace are uncertain. Everything above is conditional on drivers responding as "
        f"the model assumes."
    )
    cites.append(
        EvidenceCitation(
            kind="metric",
            ref="uncertainty.horizon_band",
            detail=f"confidence bands widen monotonically to the {brief.horizon_years:g}-year horizon",
        )
    )
    if brief.charge > 0 and not brief.has_low_income_exemption:
        points.append(
            "Failure mode #3 — political durability: a regressive flat charge with no "
            "low-income exemption is the most common trigger for public backlash and "
            "repeal. Design the exemption in before, not after, the backlash."
        )

    return Argument(
        persona="Devil's Advocate",
        role="Adversarial stress test",
        stance=Stance.challenge,
        headline="Assume it fails — here is how, and how early.",
        points=points,
        citations=cites,
        confidence=0.55,
    )


#: The full panel, in speaking order.
PANEL = (government, opposition, equity, economist, devils_advocate)


def build_arguments(brief: DebateBrief) -> list[Argument]:
    """Run the whole panel over ``brief`` and return their structured arguments."""
    return [persona(brief) for persona in PANEL]
