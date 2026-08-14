"""Schema for the scenario-presets catalogue (SPEC §3 / §27 / §28).

``GET /scenarios`` is the discoverable *menu* of ready-to-run canonical policies.
Every other endpoint requires the caller to author or compile a Policy DSL first;
nothing advertised the demo's own canonical scenarios so the UI (or a judge) could
one-click load one. This catalogue closes that gap.

Provenance (SPEC §34): the catalogue itself is a curated list of *inputs*, so the
library is **Observed** about itself. Each card embeds the real compiler output
(``compiled``), whose ``provenance`` is ``Generated`` — the compiler *structures*
text into a DSL and never produces numeric effects. No numeric model runs here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag
from ..policy.dsl import CompileResponse


class ScenarioCard(BaseModel):
    """One ready-to-run canonical policy scenario."""

    id: str = Field(description="Stable scenario key, e.g. 'congestion_charge_cbd'.")
    title: str = Field(description="Short human-facing title.")
    summary: str = Field(description="One-line description of the policy lever.")
    family: str = Field(
        description="Intervention family, derived live from the compiled DSL "
        "(road_pricing / pedestrianisation / low_emission_zone / parking_levy / "
        "transit_investment / other) so it can never drift from the compiler."
    )
    spec_sections: list[str] = Field(
        default_factory=list, description="SPEC sections this scenario exercises."
    )
    text: str = Field(description="The natural-language policy prompt a user would type.")
    objective: dict = Field(
        default_factory=dict,
        description="Optimiser objective for the composed-answer endpoints "
        "(/run, /north-star, /brief). Empty when the scenario has no numeric target.",
    )
    constraints: dict = Field(
        default_factory=dict,
        description="Optimiser constraints for the composed-answer endpoints.",
    )
    compiled: CompileResponse = Field(
        description="The real compiler output for `text` (DSL + reviewable "
        "assumptions). Provenance Generated (SPEC §34): structuring, not simulation."
    )
    simulate_body: dict = Field(
        description="Ready-to-POST body for /simulate (and any endpoint that takes a "
        "compiled `policy`): {'policy': <compiled DSL>}."
    )
    answer_body: dict = Field(
        description="Ready-to-POST body for the composed-answer endpoints "
        "(/run, /north-star, /brief): {'text', 'objective', 'constraints'}."
    )


class ScenarioLibrary(BaseModel):
    """The full curated menu of canonical demo policies."""

    provenance: MetricTag = Field(
        MetricTag.observed,
        description="The catalogue lists curated inputs, so it is Observed about "
        "itself. Per-card `compiled.provenance` is Generated (SPEC §34).",
    )
    note: str = Field(
        default=(
            "Scenario presets: the discoverable menu of canonical demo policies. "
            "Each carries its natural-language prompt, the live compiler output "
            "(DSL + reviewable assumptions), and two ready-to-POST bodies — one for "
            "/simulate and one for the composed-answer endpoints. No numeric model "
            "runs here; every quantitative figure is produced downstream by the "
            "deterministic simulation layers (SPEC §34)."
        )
    )
    count: int = Field(description="Number of scenarios in the library.")
    families: list[str] = Field(
        default_factory=list,
        description="Distinct intervention families represented, sorted.",
    )
    scenarios: list[ScenarioCard] = Field(default_factory=list)
