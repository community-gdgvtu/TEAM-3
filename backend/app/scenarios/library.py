"""Curated library of canonical demo policies (SPEC §3 / §27 / §28).

The definitions below are *inputs only* — natural-language prompts plus the
optimiser objective/constraints the composed-answer endpoints optimise against.
Everything structured (the DSL, the intervention family, the reviewable
assumptions) is produced by running the **real** ``compile_policy`` at build
time, so a scenario card can never disagree with ``POST /policy/compile``.

No numeric simulation runs here (SPEC §34); the bodies are handed to the
downstream deterministic layers by the caller.
"""

from __future__ import annotations

from ..policy import compile_policy
from .schema import ScenarioCard, ScenarioLibrary

#: (id, title, summary, spec_sections, text, objective, constraints).
#: ``text`` is the prompt a user would type; the DSL + family are compiled from it.
_DEFINITIONS: list[tuple[str, str, str, list[str], str, dict, dict]] = [
    (
        "congestion_charge_cbd",
        "CBD congestion charge (reinvested in buses)",
        "A $12 daytime charge on private vehicles entering the central cordon, "
        "with 100% of net proceeds funding buses — the flagship demo policy.",
        ["§3", "§7.5", "§28"],
        "Introduce a $12 congestion charge for private vehicles entering the "
        "central business district between 7:00 AM and 7:00 PM, beginning "
        "1 January 2027. Exempt emergency vehicles and disability permit holders. "
        "Reinvest 100% of net proceeds into buses.",
        {"reduce_transport_emissions_pct": 20},
        {"max_low_income_burden_increase_pct": 2},
    ),
    (
        "congestion_charge_general_fund",
        "CBD congestion charge (revenue to general fund)",
        "The same $12 cordon charge but with proceeds going to the general fund — "
        "the contrast that shows reinvestment, not the charge alone, drives the "
        "transit gains.",
        ["§3", "§7.5", "§21"],
        "Introduce a $12 congestion charge for private vehicles entering the "
        "central business district between 7:00 AM and 7:00 PM, beginning "
        "1 January 2027, with proceeds going to the general fund.",
        {"reduce_transport_emissions_pct": 20},
        {"max_low_income_burden_increase_pct": 2},
    ),
    (
        "pedestrianise_core",
        "Pedestrianise the CBD core",
        "Remove private-vehicle access from the inner cordon streets during the "
        "day — a hard access change rather than a price signal.",
        ["§3", "§7.5", "§7.7"],
        "Pedestrianise the central business district core: ban private vehicles "
        "from the inner cordon streets between 7:00 AM and 10:00 PM, beginning "
        "1 March 2027, with exemptions for emergency vehicles and disability "
        "permit holders.",
        {"reduce_transport_emissions_pct": 25},
        {"max_low_income_burden_increase_pct": 2},
    ),
    (
        "low_emission_zone",
        "Central low emission zone",
        "A daily charge on the most polluting vehicles inside the CBD, reinvested "
        "in buses — targets emissions more than congestion.",
        ["§3", "§7.5"],
        "Establish a low emission zone across the central business district from "
        "1 January 2027, requiring the most polluting private vehicles to pay $8 "
        "per day to drive within it. Reinvest 100% of proceeds into buses.",
        {"reduce_transport_emissions_pct": 15},
        {"max_low_income_burden_increase_pct": 2},
    ),
    (
        "workplace_parking_levy",
        "Workplace parking levy",
        "A per-space daily levy on CBD workplace parking with most revenue funding "
        "transit — an employer-side lever on car commuting.",
        ["§3", "§7.5"],
        "Introduce a workplace parking levy of $5 per space per day across the "
        "central business district from 1 April 2027. Reinvest 80% of revenue "
        "into public transport.",
        {"reduce_transport_emissions_pct": 12},
        {"max_low_income_burden_increase_pct": 2},
    ),
    (
        "bus_network_investment",
        "Bus network investment (no charge)",
        "Pure supply-side transit investment funded from the general fund — the "
        "'carrot without the stick' baseline for comparison.",
        ["§3", "§7.5"],
        "Invest heavily in the bus network: add new bus routes and increase "
        "service frequency across the city from the general fund, beginning "
        "1 January 2027.",
        {"reduce_transport_emissions_pct": 10},
        {},
    ),
]


def _build_card(
    sid: str,
    title: str,
    summary: str,
    spec_sections: list[str],
    text: str,
    objective: dict,
    constraints: dict,
) -> ScenarioCard:
    compiled = compile_policy(text)
    policy_body = compiled.policy.model_dump()
    return ScenarioCard(
        id=sid,
        title=title,
        summary=summary,
        family=compiled.policy.intervention.type.value,
        spec_sections=spec_sections,
        text=text,
        objective=objective,
        constraints=constraints,
        compiled=compiled,
        simulate_body={"policy": policy_body},
        answer_body={
            "text": text,
            "objective": objective,
            "constraints": constraints,
        },
    )


def build_library() -> ScenarioLibrary:
    """Compile every curated scenario into a ready-to-run card (deterministic)."""
    cards = [_build_card(*definition) for definition in _DEFINITIONS]
    families = sorted({card.family for card in cards})
    return ScenarioLibrary(count=len(cards), families=families, scenarios=cards)


def get_scenario(scenario_id: str) -> ScenarioCard | None:
    """Return a single scenario card by id, or ``None`` if unknown."""
    for card in build_library().scenarios:
        if card.id == scenario_id:
            return card
    return None


def scenario_ids() -> list[str]:
    """Every valid scenario id, in catalogue order."""
    return [definition[0] for definition in _DEFINITIONS]
