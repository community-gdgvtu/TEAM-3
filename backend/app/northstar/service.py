"""North-Star composition service (SPEC §37).

Assembles the minister's answer to "What happens if we implement this?" by
reusing the engine's existing deterministic layers verbatim. No new numeric
model, no LLM in any figure — this is pure orchestration (SPEC §34). Every
section embeds the *same* object the standalone endpoint returns, and a short
deterministic ``lead`` sentence is read straight off those numbers.
"""

from __future__ import annotations

from ..analogues.model import run_analogues
from ..baseline.schema import MetricTag
from ..diffusion.model import run_diffusion
from ..media import run_media
from ..microsim.model import build_microsim_report
from ..optimiser import optimise_policy
from ..parliament import build_failure_register, run_debate, simulate_brief
from ..parliament.schema import Argument, Stance
from ..policy import compile_policy
from ..policy.dsl import PolicyDSL
from ..registry.model import build_registry
from ..routers.simulate import SimulateRequest, SimulateResponse, simulate
from ..simulation.amendment import Amendment, compare_amendment
from ..simulation.shocks import Shocks
from .schema import (
    HeadlineMetric,
    NorthStarAnswer,
    NorthStarRequest,
    NorthStarSection,
    ProposedRiskAmendment,
)

# The flagship metric §37 leans on for the analogue cross-check + uncertainty fan.
_FLAGSHIP_KEY = "traffic.vehicle_trips_into_cbd"

# Dashboard tiles for the "median simulated outcome" (§37.4) — same set as /run.
_HEADLINE_KEYS: list[tuple[str, str]] = [
    ("traffic.vehicle_trips_into_cbd", "Cordon traffic (vehicles into CBD)"),
    ("emissions.daily_co2_tonnes", "Commuter CO₂"),
    ("mode_share.car_pct", "Car mode share"),
    ("transit.daily_transit_trips", "Transit ridership"),
    ("transit.peak_into_cbd_transit_trips", "Peak transit crowding"),
]

# Monte-Carlo draws for the uncertainty fan — kept modest so one North-Star call
# stays snappy while remaining seed-reproducible (SPEC §24/§34).
_UNCERTAINTY_SAMPLES = 80


def _nearest_checkpoint_months(sim: SimulateResponse, horizon_months: float) -> tuple[float, str]:
    """Snap a requested horizon to the nearest Time-Machine checkpoint."""
    best = min(sim.delta.checkpoints, key=lambda cp: abs(cp.t_months - horizon_months))
    return best.t_months, best.label


def _build_headline(sim: SimulateResponse, t_months: float) -> list[HeadlineMetric]:
    """Extract the median-outcome dashboard tiles at ``t_months`` (§37.4)."""
    by_key = {s.key: s for s in sim.delta.series}
    tiles: list[HeadlineMetric] = []
    for key, label in _HEADLINE_KEYS:
        series = by_key.get(key)
        if series is None:
            continue
        point = min(series.points, key=lambda p: abs(p.t_months - t_months))
        scale = abs(point.world_a) or 1.0
        if point.delta < -1e-6 * scale:
            direction = "down"
        elif point.delta > 1e-6 * scale:
            direction = "up"
        else:
            direction = "flat"
        tiles.append(
            HeadlineMetric(
                key=key,
                label=label,
                unit=series.unit,
                world_a=point.world_a,
                world_b=point.world_b,
                delta=point.delta,
                delta_pct=point.delta_pct,
                direction=direction,
                band=[point.low, point.high],
                tag=series.tag,
            )
        )
    return tiles


def _strongest_opposition(debate) -> Argument | None:
    """The most-confident argument that is not outright support (§37.9)."""
    against = [a for a in debate.arguments if a.stance != Stance.support]
    if not against:
        return None
    # Prefer explicit opposition; fall back to the strongest conditional/challenge.
    opposing = [a for a in against if a.stance == Stance.oppose]
    pool = opposing or against
    return max(pool, key=lambda a: a.confidence)


def _propose_risk_amendments(policy: PolicyDSL) -> list[tuple[Amendment, str, str]]:
    """Up to three distinct, risk-reducing amendments (§37.12).

    Deterministic rules over the DSL shape, each tied to a concrete risk the
    other layers surface: regressivity (§13 / microsim), mid-run crowding (event
    ledger), and public backlash / commute-cost (opinion + optimiser). No LLM.
    """
    amount = policy.intervention.amount
    has_charge = amount is not None and amount > 0
    exemptions = [e.lower() for e in policy.exemptions]
    has_low_income = any("income" in e for e in exemptions)
    has_resident = any("resident" in e for e in exemptions)
    pt_share = policy.revenue_allocation.public_transport

    proposals: list[tuple[Amendment, str, str]] = []

    if has_charge and not has_low_income:
        proposals.append(
            (
                Amendment(label="exempt low-income commuters", exempt_low_income=True),
                "distributional regressivity (SPEC §13)",
                "A flat charge falls hardest on the lowest-income commuters; exempting "
                "them collapses the regressivity ratio while keeping most traffic and "
                "climate gains.",
            )
        )
    if has_charge and pt_share < 0.99:
        proposals.append(
            (
                Amendment(label="reinvest all revenue in transit", set_public_transport_share=1.0),
                "mid-run transit crowding (event ledger)",
                "Directing the full charge revenue into transit funds the capacity ramp "
                "sooner, easing the crowding the event ledger flags as demand shifts.",
            )
        )
    if has_charge:
        proposals.append(
            (
                Amendment(label="phase in the charge (start at half)", charge_multiplier=0.5),
                "public backlash & commute-cost shock",
                "Introducing the charge at half strength softens the immediate "
                "out-of-pocket and support hit, buying time for the transit response.",
            )
        )
    # Fallbacks when there is no charge to soften.
    if not proposals and pt_share < 0.99:
        proposals.append(
            (
                Amendment(label="reinvest savings in transit", set_public_transport_share=1.0),
                "weak transit response",
                "With no charge revenue, redirecting the freed budget into transit is the "
                "main lever left to strengthen the modal shift.",
            )
        )
    if not has_charge and not has_resident and has_low_income is False:
        # A geography-fairness lever that is always structurally valid.
        proposals.append(
            (
                Amendment(label="exempt in-cordon residents", exempt_residents=True),
                "resident fairness",
                "Exempting residents inside the zone removes a fairness objection without "
                "materially changing the commuter-facing effect.",
            )
        )
    return proposals[:3]


def _tag_from_string(value: str) -> MetricTag:
    """Map a provenance string onto an allowed MetricTag (best-effort)."""
    low = value.lower()
    if "generated" in low:
        return MetricTag.generated
    if "observed" in low:
        return MetricTag.observed
    if "estimated" in low:
        return MetricTag.estimated
    return MetricTag.simulated


def run_north_star(req: NorthStarRequest) -> NorthStarAnswer:
    """Compose the full §37 minister's answer for one policy."""
    # 1. Compile (NL → DSL) unless a compiled policy was supplied.
    compiled = None
    if req.policy is not None:
        policy = req.policy
    else:
        compiled = compile_policy(req.text or "", req.jurisdiction)
        policy = compiled.policy

    shocks: Shocks | None = req.shocks

    # --- Core simulation (shared truth every section rests on) -----------------
    sim = simulate(SimulateRequest(policy=policy, shocks=shocks, seed=req.seed))
    t_months, horizon_label = _nearest_checkpoint_months(sim, req.horizon_months)

    baseline = sim.world_a.snapshot
    mechanisms = sim.event_ledger
    headline = _build_headline(sim, t_months)

    # --- Layer outputs, each the same object the standalone endpoint returns ---
    analogues = run_analogues(policy, horizon_months=t_months)
    uncertainty = _run_uncertainty(policy, shocks, t_months)
    microsim = build_microsim_report(policy)
    failure = build_failure_register(simulate_brief(policy, shocks=shocks))
    debate = run_debate(policy, shocks=shocks, seed=req.seed)
    diffusion = run_diffusion(policy, shocks=shocks)
    media = run_media(policy, shocks=shocks)
    optimiser = optimise_policy(req.objective, req.constraints, shocks=shocks)

    opposition = _strongest_opposition(debate)

    # --- Risk-reducing amendments + each amendment's re-simulated effect -------
    amendments: list[ProposedRiskAmendment] = []
    for amendment, risk, rationale in _propose_risk_amendments(policy):
        amendments.append(
            ProposedRiskAmendment(
                label=amendment.label,
                targets_risk=risk,
                rationale=rationale,
                comparison=compare_amendment(policy, amendment, shocks=shocks),
            )
        )

    # --- Every assumption + guardrail behind the conclusions (§37.15) ----------
    registry = build_registry()
    evidence = {
        "assumption_index": [a.model_dump() for a in registry.assumption_index],
        "guardrails": [g.model_dump() for g in registry.guardrails],
        "data_sources": [d.model_dump() for d in registry.data_sources],
        "counts": registry.counts,
        "llm_touches_numbers": any(
            getattr(m, "llm_touches_numbers", False) for m in registry.models
        ),
        "note": (
            "Assumptions read live from the running model dataclasses via /registry "
            "(SPEC §33); every numeric model asserts llm_touches_numbers=False (SPEC §34)."
        ),
    }

    sections = _build_sections(
        horizon_label=horizon_label,
        baseline=baseline,
        analogues=analogues,
        mechanisms=mechanisms,
        headline=headline,
        uncertainty=uncertainty,
        microsim=microsim,
        failure=failure,
        opposition=opposition,
        diffusion=diffusion,
        media=media,
        amendments=amendments,
        optimiser=optimiser,
        evidence=evidence,
    )

    return NorthStarAnswer(
        policy_id=policy.id,
        question=req.question,
        horizon_months=t_months,
        horizon_label=horizon_label,
        compiled=compiled,
        sections=sections,
        baseline=baseline,
        analogues=analogues,
        mechanisms=mechanisms,
        median_outcome=headline,
        delta=sim.delta,
        uncertainty=uncertainty,
        winners=microsim,
        failure_modes=failure,
        opposition_argument=opposition,
        debate=debate,
        opinion_evolution=diffusion,
        media=media,
        amendments=amendments,
        best_configuration=optimiser,
        evidence=evidence,
    )


def _run_uncertainty(policy: PolicyDSL, shocks: Shocks | None, t_months: float):
    """Uncertainty fan on the flagship cordon-traffic metric (§37.5)."""
    from ..uncertainty import run_uncertainty

    return run_uncertainty(
        policy,
        _FLAGSHIP_KEY,
        shocks=shocks,
        horizon_months=t_months,
        samples=_UNCERTAINTY_SAMPLES,
    )


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"


def _build_sections(
    *,
    horizon_label,
    baseline,
    analogues,
    mechanisms,
    headline,
    uncertainty,
    microsim,
    failure,
    opposition,
    diffusion,
    media,
    amendments,
    optimiser,
    evidence,
) -> list[NorthStarSection]:
    """The fixed §37 narrative, each line with a deterministic one-sentence lead."""
    # §37.4 headline synthesis.
    traffic_tile = next((t for t in headline if t.key == _FLAGSHIP_KEY), None)
    co2_tile = next((t for t in headline if t.key == "emissions.daily_co2_tonnes"), None)
    outcome_lead = "; ".join(
        f"{t.label} {_pct(t.delta_pct)}" for t in (traffic_tile, co2_tile) if t is not None
    ) or "policy shifts the headline metrics at the chosen horizon."

    top_failure = failure.failure_modes[0] if failure.failure_modes else None
    best_id = optimiser.recommendations.best_balanced if optimiser.recommendations else None
    best_candidate = next((c for c in optimiser.candidates if c.policy_id == best_id), None)

    lead_amendments = (
        ", ".join(a.label for a in amendments) if amendments else "no structural amendment needed"
    )

    return [
        NorthStarSection(
            order=1,
            question="Here is the baseline.",
            lead=(
                f"World A: {baseline.traffic.vehicle_trips_into_cbd:,} vehicles/day into the "
                f"cordon, {baseline.emissions.daily_co2_tonnes:.1f} t commuter CO₂/day, "
                f"car mode share {baseline.mode_share.car_pct:.1f}%."
            ),
            backs="baseline",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=2,
            question="Here are the historical analogues.",
            lead=(
                f"Comparable real schemes pool to ≈{analogues.estimated_effect_pct:.0f}% cordon "
                f"traffic (CI {analogues.ci_low_pct:.0f}…{analogues.ci_high_pct:.0f}%), "
                f"{analogues.analogue_quality} analogue quality."
            ),
            backs="analogues",
            tag=MetricTag.estimated,
        ),
        NorthStarSection(
            order=3,
            question="Here are the mechanisms through which the policy acts.",
            lead=(
                f"{len(mechanisms.events)} structured event(s) trace the causal chain "
                "(mode shift → revenue → transit capacity → crowding relief)."
                if mechanisms.events
                else "The policy produces no threshold-crossing events at this configuration."
            ),
            backs="mechanisms",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=4,
            question="Here is the median simulated outcome.",
            lead=f"At {horizon_label}: {outcome_lead}.",
            backs="median_outcome / delta",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=5,
            question="Here is the uncertainty.",
            lead=(
                f"Flagship metric median Δ {uncertainty.median:+.0f} {uncertainty.unit}; "
                f"the fan widens with horizon across "
                f"{len(uncertainty.fan)} checkpoints (SPEC §34)."
            ),
            backs="uncertainty",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=6,
            question="Here is who benefits.",
            lead=(
                f"{microsim.winners:,} commuters better off"
                + (f"; largest gains: {microsim.biggest_winner}." if microsim.biggest_winner else ".")
            ),
            backs="winners",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=7,
            question="Here is who loses.",
            lead=(
                f"{microsim.losers:,} commuters worse off; "
                f"regressivity ratio {microsim.regressivity_ratio:.1f}"
                + (f"; worst hit: {microsim.worst_hit}." if microsim.worst_hit else ".")
            ),
            backs="winners",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=8,
            question="Here is where the policy is most likely to fail.",
            lead=(
                f"Top failure mode: {top_failure.risk} (risk score {top_failure.risk_score:.2f}); "
                f"mitigation — {top_failure.mitigation}."
                if top_failure is not None
                else "No material failure modes surfaced for this configuration."
            ),
            backs="failure_modes",
            tag=MetricTag.estimated,
        ),
        NorthStarSection(
            order=9,
            question="Here is the opposition's strongest argument.",
            lead=(
                f"{opposition.persona} ({opposition.stance.value}): {opposition.headline}"
                if opposition is not None
                else "No credible opposition argument survives the evidence at this configuration."
            ),
            backs="opposition_argument / debate",
            tag=MetricTag.generated,
        ),
        NorthStarSection(
            order=10,
            question="Here is how public opinion may evolve under these assumptions.",
            lead=(
                f"Citizen net support drifts {diffusion.initial_net_support:+.2f} → "
                f"{diffusion.final_net_support:+.2f} over {diffusion.rounds} diffusion rounds."
            ),
            backs="opinion_evolution",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=11,
            question="Here are plausible media narratives if these simulated events occur.",
            lead=(
                f"{sum(len(s.headlines) for s in media.scenarios)} SIMULATED headline(s) "
                f"across {len(media.scenarios)} horizon(s) — every one labelled SIMULATED (SPEC §34)."
            ),
            backs="media",
            tag=MetricTag.generated,
        ),
        NorthStarSection(
            order=12,
            question="Here are three amendments that reduce the largest risks.",
            lead=f"Proposed: {lead_amendments}.",
            backs="amendments",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=13,
            question="Here is what happens if we adopt each amendment.",
            lead=(
                f"Each amendment re-simulated through the same A/B/Δ path "
                f"({len(amendments)} comparison(s))."
                if amendments
                else "No amendment to re-simulate; the base policy already covers the main risks."
            ),
            backs="amendments[*].comparison",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=14,
            question="Here is the policy configuration that best satisfies your stated goals.",
            lead=(
                f"Best-balanced: {best_candidate.label} "
                f"({'feasible' if best_candidate.feasible else 'infeasible under constraints'})."
                if best_candidate is not None
                else f"Optimiser searched {optimiser.n_candidates} candidates; "
                "no single best-balanced pick under the stated goals."
            ),
            backs="best_configuration",
            tag=MetricTag.simulated,
        ),
        NorthStarSection(
            order=15,
            question="Here is every assumption and piece of evidence behind those conclusions.",
            lead=(
                f"{len(evidence['assumption_index'])} documented assumptions and "
                f"{len(evidence['guardrails'])} SPEC §34 guardrails; "
                "no LLM touches any number."
            ),
            backs="evidence",
            tag=MetricTag.observed,
        ),
    ]
