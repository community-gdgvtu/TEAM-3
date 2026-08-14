"""Orchestrate a Model Parliament debate (ROADMAP M5, SPEC §11/§12).

Pipeline: run the deterministic simulation for the policy → build the shared
:class:`~app.parliament.personas.DebateBrief` (Δ metrics + event ledger) → let
each persona construct its evidence-grounded argument → render each argument as
prose (LLM if a key is configured, deterministic template otherwise) →
synthesise a tally and summary.

Guardrail (SPEC §34): the simulation and every cited figure are deterministic and
Simulated; only the speech wording may be LLM-produced, and the fallback keeps
the endpoint working with no key.
"""

from __future__ import annotations

from ..baseline.model import compute_baseline
from ..baseline.timeseries import build_timeseries
from ..config import settings
from ..simulation.compare import build_delta
from ..simulation.events import build_event_ledger
from ..simulation.model import compute_world_b
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from ..policy.dsl import PolicyDSL
from .llm import (
    ParliamentLLMUnavailable,
    generate_answer,
    generate_speech,
    template_answer,
    template_speech,
)
from .personas import DebateBrief, PANEL_BY_NAME, build_arguments
from .schema import Argument, AskResponse, DebateResponse, Stance


def simulate_brief(policy: PolicyDSL, shocks: Shocks | None = None) -> DebateBrief:
    """Run the deterministic simulation and package it as a shared debate brief.

    Reused by both the debate and the Failure Mode Register so every parliament
    surface reads exactly the same Simulated evidence (SPEC §11/§12).
    """
    params, trend = apply_shocks(shocks)
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=params, reinvestment=True)
    b_ts = build_world_b_timeline(policy, baseline=base, params=params, trend=trend)
    delta = build_delta(base_ts, b_ts)
    ledger = build_event_ledger(policy, base, delta)
    return DebateBrief(policy, base, b_full, delta, ledger)


def _motion(policy: PolicyDSL) -> str:
    iv = policy.intervention
    charge = (
        f" with a {iv.amount:g} {iv.currency} charge"
        if iv.amount
        else ""
    )
    return (
        f"That this House approves the {iv.type.value.replace('_', ' ')} of the "
        f"{iv.geographic_zone.replace('_', ' ')}{charge}."
    )


def _render_speeches(arguments: list[Argument]) -> str:
    """Fill each argument's ``speech`` in place; return the method used ('llm'/'template')."""
    use_llm = settings.llm_enabled
    method = "template"
    for arg in arguments:
        if use_llm:
            try:
                arg.speech = generate_speech(
                    arg.persona, arg.role, arg.stance.value, arg.points
                )
                method = "llm"
                continue
            except ParliamentLLMUnavailable:
                # First failure: stop trying the LLM for the rest of the debate and
                # fall back deterministically, so we never half-populate.
                use_llm = False
        arg.speech = template_speech(arg.headline, arg.points)
    return method


def _summarise(policy: PolicyDSL, arguments: list[Argument], tally: dict) -> str:
    support = tally.get("support", 0)
    oppose = tally.get("oppose", 0)
    conditional = tally.get("conditional", 0)
    da = next((a for a in arguments if a.stance == Stance.challenge), None)
    lead = (
        "The chamber leans in favour"
        if support > oppose
        else "The chamber leans against"
        if oppose > support
        else "The chamber is split"
    )
    cond_note = (
        f" {conditional} member(s) back it only with amendments — chiefly on "
        f"distributional protection and transit sequencing."
        if conditional
        else ""
    )
    risk = (
        f" The Devil's Advocate flags the adaptation gap as the primary failure mode."
        if da
        else ""
    )
    return (
        f"{lead} ({support} for, {oppose} against, {conditional} conditional)."
        f"{cond_note}{risk} All positions are grounded in the same Simulated "
        f"evidence base, so disagreement is about values and sequencing, not facts."
    )


def run_debate(
    policy: PolicyDSL,
    shocks: Shocks | None = None,
    seed: int | None = None,
) -> DebateResponse:
    """Run the full parliament debate for ``policy`` and return the structured result."""
    brief = simulate_brief(policy, shocks)
    arguments = build_arguments(brief)
    method = _render_speeches(arguments)

    tally: dict = {}
    for a in arguments:
        tally[a.stance.value] = tally.get(a.stance.value, 0) + 1

    return DebateResponse(
        policy_id=policy.id,
        motion=_motion(policy),
        method=method,
        arguments=arguments,
        tally=tally,
        summary=_summarise(policy, arguments, tally),
    )


def ask_persona(
    policy: PolicyDSL,
    persona: str,
    question: str,
    shocks: Shocks | None = None,
) -> AskResponse:
    """Answer ``question`` in ``persona``'s voice, grounded in their own argument.

    Reruns the same deterministic simulation and persona logic as
    :func:`run_debate` — the answer prose is the only thing that differs (a
    direct response to ``question`` rather than the set-piece speech) — so the
    guardrail is identical: numbers come from the model, the LLM only phrases
    them, and the endpoint always answers even with no key configured.
    """
    build_fn = PANEL_BY_NAME.get(persona)
    if build_fn is None:
        raise ValueError(
            f"Unknown persona {persona!r}. Choose one of: {', '.join(PANEL_BY_NAME)}."
        )
    brief = simulate_brief(policy, shocks)
    arg = build_fn(brief)

    method = "template"
    answer = template_answer(arg.headline, arg.points, question)
    if settings.llm_enabled:
        try:
            answer = generate_answer(arg.persona, arg.role, arg.stance.value, arg.points, question)
            method = "llm"
        except ParliamentLLMUnavailable:
            pass

    return AskResponse(
        persona=arg.persona,
        role=arg.role,
        stance=arg.stance,
        question=question,
        answer=answer,
        method=method,
        citations=arg.citations,
    )
