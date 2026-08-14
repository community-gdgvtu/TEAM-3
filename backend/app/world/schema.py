"""Pydantic schemas for the composed Baseline World Model (SPEC §5 / §28.2).

``GET /world`` returns **World A's structural composition** — the browsable
digital twin the demo renders (§28.2: "roads, transit, population cohorts,
businesses") — organised as the six SPEC §5 layers (Population, Economy,
Geography, Environment, Institutions, Society).

This is *not* a new forecast. Every number is either:

* a **count / distribution read directly from the synthetic dataset**
  (``data/city/*``) — describing what is in the world, tagged ``Simulated``
  because the city itself is synthetically generated (consistent with the
  Data Fabric, SPEC §4), or
* the deterministic **baseline agent-based model's** own aggregate output
  (emissions, mode share) — also ``Simulated``, or
* an **Observed** transparency description of how an institutional / society
  actor is *modelled* (parliament & diffusion agents), with any behavioural
  prior tagged ``Estimated``.

No LLM produces any number here (SPEC §34). Gaps are surfaced honestly in each
layer's ``not_modelled`` list rather than fabricated.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MetricTag(str, Enum):
    """Provenance class for a single field (SPEC §8 tagging table)."""

    observed = "Observed"
    estimated = "Estimated"
    simulated = "Simulated"
    generated = "Generated"


class Distribution(BaseModel):
    """A named categorical breakdown (label -> count) with percentages."""

    counts: dict[str, int] = Field(default_factory=dict)
    pct: dict[str, float] = Field(default_factory=dict)


class PopulationLayer(BaseModel):
    """SPEC §5 Population layer — who lives and commutes in World A."""

    provenance: MetricTag = MetricTag.simulated
    total_agents: int = Field(description="Synthetic commuter micro-agents (SPEC §6).")
    commuters: int
    cbd_commuters: int = Field(description="Agents whose work trip enters the central district.")
    age_years: dict[str, float] = Field(description="min / max / mean of agent age.")
    age_bands: Distribution
    household_size: Distribution
    income_monthly: dict[str, float] = Field(
        description="min / median / mean monthly income (synthetic currency units)."
    )
    income_bands: Distribution
    income_deciles: list[float] = Field(
        description="9 decile boundaries (10th..90th pct) of monthly income."
    )
    occupations: Distribution = Field(description="Occupation mix across the population.")
    mobility: dict[str, float] = Field(
        description="Share (%) with car access / transit access / both."
    )
    commute: dict[str, float] = Field(
        description="Mean commute distance (km) and CBD-commuter share (%)."
    )
    behavioural_priors: dict[str, float] = Field(
        description="Population-mean risk_aversion / price_sensitivity / policy_salience."
    )
    not_modelled: list[str] = Field(default_factory=list)


class EconomyLayer(BaseModel):
    """SPEC §5 Economy layer — sectors, jobs and wages in World A."""

    provenance: MetricTag = MetricTag.simulated
    total_jobs_city: int = Field(description="Jobs across all zones (city scale, from zone table).")
    cbd_jobs: int
    cbd_job_share_pct: float
    sectors: Distribution = Field(
        description="Employment grouped into economic sectors (from occupation mix)."
    )
    wages_monthly_by_band: dict[str, float] = Field(
        description="Mean monthly income per income band (proxy for wage level)."
    )
    note: str = ""
    not_modelled: list[str] = Field(default_factory=list)


class GeographyLayer(BaseModel):
    """SPEC §5 Geography layer — the physical city (§28.2 render targets)."""

    provenance: MetricTag = MetricTag.simulated
    zones: int
    cbd_zones: int
    land_use: Distribution = Field(description="Zone land-use mix.")
    roads: dict[str, float] = Field(
        description="Link count, total km, mean lanes, total capacity, cordon-crossing links."
    )
    road_classes: Distribution
    buildings: dict[str, float] = Field(
        description="Building count and mean height (m)."
    )
    building_types: Distribution
    business_locations: dict[str, float] = Field(
        description="Commercial/mixed zone count and total CBD jobs (business proxy)."
    )
    transit: dict[str, float] = Field(
        description="Population share (%) with transit access; explicit line network status."
    )
    not_modelled: list[str] = Field(default_factory=list)


class EnvironmentLayer(BaseModel):
    """SPEC §5 Environment layer — baseline emissions & land/water state."""

    provenance: MetricTag = MetricTag.simulated
    commuter_co2: dict[str, float] = Field(
        description="Baseline daily/annual commuter CO2 (tonnes) and kg/km, from the ABM."
    )
    land_use: Distribution = Field(description="Zone land-use mix incl. green space.")
    green_space_zones: int
    water_present: bool = Field(description="Whether a water/flood layer exists in the twin.")
    not_modelled: list[str] = Field(default_factory=list)


class InstitutionsLayer(BaseModel):
    """SPEC §5 Institutions layer — the governance agents that are *modelled*."""

    provenance: MetricTag = MetricTag.observed
    note: str
    parliament_agents: list[str] = Field(description="Model Parliament participants (SPEC §11).")
    institutional_agents: list[str] = Field(
        description="Multi-agent institutional reviewers beyond parliament (SPEC §18)."
    )
    not_modelled: list[str] = Field(default_factory=list)


class SocietyActor(BaseModel):
    """One modelled society actor with its documented opinion prior."""

    id: str
    kind: str
    label: str
    prior: float = Field(description="Opinion prior in [-1, 1] (Estimated).")
    rationale: str


class SocietyLayer(BaseModel):
    """SPEC §5 Society layer — opinion, media and civic actors (as modelled)."""

    provenance: MetricTag = MetricTag.estimated
    note: str
    opinion_priors_by_income_band: dict[str, float] = Field(
        description="Baseline opinion prior per income band (Estimated, from the cohort model)."
    )
    media_environment: list[str] = Field(
        description="Editorial archetypes the simulated media layer spans (SPEC §15)."
    )
    civic_actors: list[SocietyActor] = Field(
        description="Business / community / union / influencer / institutional actors (SPEC §14)."
    )
    not_modelled: list[str] = Field(default_factory=list)


class WorldModel(BaseModel):
    """The composed Baseline World Model (SPEC §5 / §28.2)."""

    world: str = Field("A", description="'A' = baseline, no intervention (SPEC §5).")
    provenance: MetricTag = Field(
        MetricTag.simulated,
        description=(
            "Structural composition of the synthetic World A. Counts/distributions "
            "read from the synthetic dataset (Simulated city); institutional/society "
            "layers are Observed descriptions of how agents are modelled. No LLM "
            "produced any number (SPEC §34)."
        ),
    )
    note: str = Field(
        default=(
            "World A digital twin composed deterministically from the synthetic "
            "city dataset and the baseline agent-based model. This is a structural "
            "snapshot, not a forecast."
        )
    )
    layer_selection: str = Field(
        description="How the smallest-sufficient layer set is chosen (SPEC §5)."
    )
    layers_returned: list[str]
    population: PopulationLayer | None = None
    economy: EconomyLayer | None = None
    geography: GeographyLayer | None = None
    environment: EnvironmentLayer | None = None
    institutions: InstitutionsLayer | None = None
    society: SocietyLayer | None = None
