"""Scenario orchestrator (SPEC §28/§29).

Composes the engine's existing deterministic layers into the single killer-demo
narrative. Nothing here computes a *new* number: it reuses ``/policy/compile``,
``/simulate``, ``/public``, ``/parliament/debate``, the amendment comparison and
``/media`` so every section rests on the **same** compiled policy and the **same**
simulation — which is exactly why the dashboard, parliament and media can never
disagree (SPEC §34 cross-layer consistency).
"""

from __future__ import annotations

from ..media import run_media
from ..opinion import compute_public_opinion
from ..parliament import run_debate
from ..policy import compile_policy
from ..policy.dsl import PolicyDSL
from ..routers.simulate import SimulateRequest, SimulateResponse, simulate
from ..simulation.amendment import Amendment, compare_amendment
from .schema import (
    HeadlineMetric,
    NarrativeBeat,
    ProposedAmendment,
    RunRequest,
    RunResponse,
)

# Dashboard tiles the §29 demo scrubs to — cordon traffic, climate, mode split,
# transit ridership and the crowding the event ledger warns about.
_HEADLINE_KEYS: list[tuple[str, str]] = [
    ("traffic.vehicle_trips_into_cbd", "Cordon traffic (vehicles into CBD)"),
    ("emissions.daily_co2_tonnes", "Commuter CO₂"),
    ("mode_share.car_pct", "Car mode share"),
    ("transit.daily_transit_trips", "Transit ridership"),
    ("transit.peak_into_cbd_transit_trips", "Peak transit crowding"),
]


def _nearest_checkpoint_months(sim: SimulateResponse, horizon_months: float) -> tuple[float, str]:
    """Snap a requested horizon to the nearest Time-Machine checkpoint."""
    checkpoints = sim.delta.checkpoints
    best = min(checkpoints, key=lambda cp: abs(cp.t_months - horizon_months))
    return best.t_months, best.label


def _build_headline(sim: SimulateResponse, t_months: float) -> list[HeadlineMetric]:
    """Extract the dashboard tiles at ``t_months`` from the simulation delta."""
    by_key = {s.key: s for s in sim.delta.series}
    tiles: list[HeadlineMetric] = []
    for key, label in _HEADLINE_KEYS:
        series = by_key.get(key)
        if series is None:
            continue
        point = min(series.points, key=lambda p: abs(p.t_months - t_months))
        # Direction relative to the baseline magnitude (flat when the shift is tiny).
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


def _propose_amendment(policy: PolicyDSL) -> tuple[Amendment | None, str, str]:
    """Deterministically derive the parliament's default amendment (SPEC §29).

    Mirrors the killer-demo beat: a flat charge is regressive, so the equity
    advocate's first move is to exempt low-income commuters. Falls back to
    directing revenue into transit when equity is already handled.
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
            "improving distributional fairness (SPEC §29 amendment beat).",
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
        "transit; no structural amendment is proposed by default.",
    )


def run_scenario(req: RunRequest) -> RunResponse:
    """Run the full §29 demo pipeline for a single policy and package it."""
    # 1. Compile (NL → DSL) unless a compiled policy was supplied.
    compiled = None
    if req.policy is not None:
        policy = req.policy
    else:
        compiled = compile_policy(req.text or "", req.jurisdiction)
        policy = compiled.policy

    # 2. Core simulation (World A / B / Δ + event ledger) — reuse /simulate verbatim
    #    so the shared numbers are literally identical to the standalone endpoint.
    sim = simulate(SimulateRequest(policy=policy, shocks=req.shocks, seed=req.seed))

    # 3. Public reaction + 4. parliament, both reading the same policy/shocks.
    public = compute_public_opinion(policy)
    parliament = run_debate(policy, shocks=req.shocks, seed=req.seed)

    # 5. Amendment (caller override or auto-derived) + re-simulation.
    if req.amendment is not None:
        amendment, source = req.amendment, "caller"
        rationale = "Caller-supplied amendment."
    else:
        amendment, source, rationale = _propose_amendment(policy)

    comparison = (
        compare_amendment(policy, amendment, shocks=req.shocks)
        if amendment is not None
        else None
    )
    proposed = ProposedAmendment(
        proposed=amendment is not None,
        source=source,
        rationale=rationale,
        amendment=amendment,
        comparison=comparison,
    )

    # 6. Simulated media coverage (both horizons).
    media = run_media(policy, shocks=req.shocks)

    # Dashboard at the requested horizon.
    t_months, horizon_label = _nearest_checkpoint_months(sim, req.horizon_months)
    headline = _build_headline(sim, t_months)

    narrative = _build_narrative(horizon_label, parliament, proposed)

    return RunResponse(
        policy_id=policy.id,
        horizon_months=t_months,
        horizon_label=horizon_label,
        compiled=compiled,
        narrative=narrative,
        headline=headline,
        net_support=public.overall.net_support,
        simulation=sim,
        public=public,
        parliament=parliament,
        amendment=proposed,
        media=media,
    )


def _build_narrative(
    horizon_label: str,
    parliament,
    amendment: ProposedAmendment,
) -> list[NarrativeBeat]:
    """The §29 storyline, with beats pointing at the sections that back them."""
    amend_line = (
        f"Parliament proposes: {amendment.amendment.label}."
        if amendment.amendment is not None
        else "No amendment proposed — the policy already covers the equity gap."
    )
    return [
        NarrativeBeat(
            timecode="0–10s",
            stage="Compile policy",
            section="compiled / simulation.policy_id",
            description="Natural-language policy is structured into a reviewable DSL.",
        ),
        NarrativeBeat(
            timecode="10–30s",
            stage="Run counterfactual + scrub timeline",
            section="headline / simulation",
            description=f"World A vs World B across the timeline; dashboard at {horizon_label}.",
        ),
        NarrativeBeat(
            timecode="20–30s",
            stage="Public reaction",
            section="public / net_support",
            description="Cohort opinion resolves into an overall support split.",
        ),
        NarrativeBeat(
            timecode="30–40s",
            stage="Parliament",
            section="parliament",
            description=f"Adversarial debate: {parliament.summary}",
        ),
        NarrativeBeat(
            timecode="40–50s",
            stage="Apply amendment + re-simulate",
            section="amendment",
            description=amend_line,
        ),
        NarrativeBeat(
            timecode="50–60s",
            stage="Media future",
            section="media",
            description="Simulated press feed at Month 5 and Year 2 (labelled SIMULATED).",
        ),
    ]
