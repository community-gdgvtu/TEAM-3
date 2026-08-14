"""Deterministic composition of the Baseline World Model (SPEC §5 / §28.2).

Reads the synthetic city dataset (``data/city/*``) and the baseline
agent-based model, and assembles World A into the six SPEC §5 layers. Pure
counts / distributions / model aggregates — **no LLM, no forecast** (SPEC §34).
Cached, so repeated calls are byte-identical for a given dataset.
"""

from __future__ import annotations

import statistics
from collections import Counter
from functools import lru_cache

from ..baseline import cached_baseline
from ..dataset import (
    cbd_zone_ids,
    data_dir,
    load_buildings,
    load_roads,
    load_zones,
    population_agents,
)
from ..opinion.params import OpinionParams
from .schema import (
    Distribution,
    EconomyLayer,
    EnvironmentLayer,
    GeographyLayer,
    InstitutionsLayer,
    PopulationLayer,
    SocietyActor,
    SocietyLayer,
    WorldModel,
)

# All six SPEC §5 layers, in canonical order.
ALL_LAYERS = ("population", "economy", "geography", "environment", "institutions", "society")

# Occupation -> economic sector map (SPEC §5 Economy: "sectors"). Documented,
# deterministic grouping of the synthetic occupations into coarse sectors.
_SECTOR_OF = {
    "nurse": "health & care",
    "physician": "health & care",
    "care_worker": "health & care",
    "teacher": "education",
    "trades": "construction & trades",
    "technician": "construction & trades",
    "retail_worker": "retail & hospitality",
    "hospitality": "retail & hospitality",
    "cleaner": "retail & hospitality",
    "manager": "professional & business",
    "administrator": "professional & business",
    "clerk": "professional & business",
    "analyst": "professional & business",
    "designer": "professional & business",
    "engineer": "professional & business",
    "executive": "professional & business",
    "lawyer": "professional & business",
    "driver": "transport & logistics",
}

_BAND_ORDER = ["low", "lower-middle", "middle", "upper-middle", "upper"]


def _distribution(counter: Counter, order: list[str] | None = None) -> Distribution:
    """Build a Distribution (counts + percentages) from a Counter."""
    total = sum(counter.values()) or 1
    keys = order if order is not None else [k for k, _ in counter.most_common()]
    counts = {k: int(counter.get(k, 0)) for k in keys}
    pct = {k: round(100.0 * counts[k] / total, 1) for k in keys}
    return Distribution(counts=counts, pct=pct)


def _deciles(values: list[float]) -> list[float]:
    """9 decile boundaries (10th..90th percentile) of ``values``."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return []
    out = []
    for d in range(1, 10):
        # linear-interpolation percentile (deterministic)
        rank = d / 10.0 * (n - 1)
        lo = int(rank)
        frac = rank - lo
        hi = min(lo + 1, n - 1)
        out.append(round(s[lo] + frac * (s[hi] - s[lo]), 1))
    return out


def _build_population() -> PopulationLayer:
    agents = population_agents()
    n = len(agents)
    ages = [a["age"] for a in agents]
    incomes = [a["income"] for a in agents]

    age_bands = Counter()
    for a in ages:
        if a < 30:
            age_bands["18-29"] += 1
        elif a < 45:
            age_bands["30-44"] += 1
        elif a < 65:
            age_bands["45-64"] += 1
        else:
            age_bands["65+"] += 1

    hh = Counter(str(a["household_size"]) for a in agents)
    hh_order = sorted(hh, key=lambda k: int(k))

    car = sum(1 for a in agents if a["car_access"])
    transit = sum(1 for a in agents if a["public_transit_access"])
    both = sum(1 for a in agents if a["car_access"] and a["public_transit_access"])
    cbd = sum(1 for a in agents if a["commutes_into_cbd"])

    def _mean(field: str) -> float:
        return round(statistics.fmean(a[field] for a in agents), 3)

    return PopulationLayer(
        total_agents=n,
        commuters=n,
        cbd_commuters=cbd,
        age_years={
            "min": float(min(ages)),
            "max": float(max(ages)),
            "mean": round(statistics.fmean(ages), 1),
        },
        age_bands=_distribution(age_bands, ["18-29", "30-44", "45-64", "65+"]),
        household_size=_distribution(hh, hh_order),
        income_monthly={
            "min": float(min(incomes)),
            "median": float(statistics.median(incomes)),
            "mean": round(statistics.fmean(incomes), 1),
        },
        income_bands=_distribution(Counter(a["income_band"] for a in agents), _BAND_ORDER),
        income_deciles=_deciles(incomes),
        occupations=_distribution(Counter(a["occupation"] for a in agents)),
        mobility={
            "car_access_pct": round(100.0 * car / n, 1),
            "transit_access_pct": round(100.0 * transit / n, 1),
            "both_pct": round(100.0 * both / n, 1),
        },
        commute={
            "mean_distance_km": round(statistics.fmean(a["commute_distance_km"] for a in agents), 2),
            "cbd_commuter_pct": round(100.0 * cbd / n, 1),
        },
        behavioural_priors={
            "risk_aversion": _mean("risk_aversion"),
            "price_sensitivity": _mean("price_sensitivity"),
            "policy_salience": _mean("policy_salience"),
        },
        not_modelled=[
            "education attainment (not in synthetic population)",
            "disability / access needs (SPEC §5 lists it; not generated)",
            "tenure / housing status (not generated)",
        ],
    )


def _build_economy() -> EconomyLayer:
    agents = population_agents()
    zones = load_zones()["features"]
    cbd = cbd_zone_ids()
    total_jobs = sum(f["properties"]["jobs"] for f in zones)
    cbd_jobs = sum(f["properties"]["jobs"] for f in zones if f["properties"]["zone_id"] in cbd)

    sectors = Counter(_SECTOR_OF.get(a["occupation"], "other") for a in agents)

    wages: dict[str, float] = {}
    for band in _BAND_ORDER:
        band_incomes = [a["income"] for a in agents if a["income_band"] == band]
        if band_incomes:
            wages[band] = round(statistics.fmean(band_incomes), 1)

    return EconomyLayer(
        total_jobs_city=int(total_jobs),
        cbd_jobs=int(cbd_jobs),
        cbd_job_share_pct=round(100.0 * cbd_jobs / (total_jobs or 1), 1),
        sectors=_distribution(sectors),
        wages_monthly_by_band=wages,
        note=(
            "Employment sectors are the synthetic occupation mix grouped by a "
            "documented map; wages proxied by mean income per band. The monetary "
            "spillover model (revenue, spend, logistics) lives in /economy (SPEC §7.4)."
        ),
        not_modelled=[
            "firms / firm-level structure (agents are workers, not firms)",
            "household expenditure & prices (partly in /economy §7.4)",
            "tax flows & government spending (charge revenue handled in /simulate)",
        ],
    )


def _build_geography() -> GeographyLayer:
    zones = load_zones()["features"]
    roads = load_roads()["features"]
    buildings = load_buildings()["features"]
    cbd = cbd_zone_ids()

    land_use = Counter(f["properties"]["land_use"] for f in zones)
    road_classes = Counter(f["properties"]["road_class"] for f in roads)
    total_km = sum(f["properties"]["length_km"] for f in roads)
    total_cap = sum(f["properties"]["capacity_veh_per_hr"] for f in roads)
    mean_lanes = statistics.fmean(f["properties"]["lanes"] for f in roads)
    cordon_links = sum(1 for f in roads if f["properties"].get("crosses_cordon"))

    bld_types = Counter(f["properties"].get("k", "unknown") for f in buildings)
    mean_h = statistics.fmean(f["properties"].get("h", 0.0) for f in buildings)

    commercial_zones = sum(
        1 for f in zones if f["properties"]["land_use"] in ("commercial", "mixed")
    )
    cbd_jobs = sum(f["properties"]["jobs"] for f in zones if f["properties"]["zone_id"] in cbd)

    agents = population_agents()
    transit_pct = round(100.0 * sum(a["public_transit_access"] for a in agents) / (len(agents) or 1), 1)

    return GeographyLayer(
        zones=len(zones),
        cbd_zones=len(cbd),
        land_use=_distribution(land_use),
        roads={
            "links": len(roads),
            "total_km": round(total_km, 1),
            "mean_lanes": round(mean_lanes, 2),
            "total_capacity_veh_per_hr": round(total_cap, 0),
            "cordon_crossing_links": cordon_links,
        },
        road_classes=_distribution(road_classes),
        buildings={
            "count": len(buildings),
            "mean_height_m": round(mean_h, 1),
        },
        building_types=_distribution(bld_types),
        business_locations={
            "commercial_or_mixed_zones": commercial_zones,
            "cbd_jobs": int(cbd_jobs),
        },
        transit={
            "population_access_pct": transit_pct,
            "explicit_line_network": 0.0,
        },
        not_modelled=[
            "explicit transit line/route geometry (access is a per-agent flag, "
            "no route network file)",
            "schools / hospitals / public services as distinct POIs (only zone "
            "land-use categories exist)",
            "parcels (buildings are point features, not cadastral parcels)",
        ],
    )


def _build_environment() -> EnvironmentLayer:
    b = cached_baseline()
    zones = load_zones()["features"]
    land_use = Counter(f["properties"]["land_use"] for f in zones)
    green = land_use.get("green_space", 0)

    # water/flood layer presence (file may or may not exist in the dataset)
    water = (data_dir() / "water.geojson").exists()

    return EnvironmentLayer(
        commuter_co2={
            "daily_tonnes": b.emissions.daily_co2_tonnes,
            "annual_tonnes": b.emissions.annual_co2_tonnes,
            "kg_per_km": b.emissions.co2_kg_per_km,
        },
        land_use=_distribution(land_use),
        green_space_zones=int(green),
        water_present=water,
        not_modelled=[
            "air-quality index / pollutant concentrations (only a commuter-CO2 "
            "proxy; spatial dispersion proxy lives in /spatial §7.7)",
            "energy demand / grid",
            "temperature & flooding dynamics (a water layer exists for rendering "
            "but no flood model; flood is a /stress-test scenario, not a state)",
        ],
    )


def _build_institutions() -> InstitutionsLayer:
    return InstitutionsLayer(
        note=(
            "Institutions are represented as deterministic decision agents, not "
            "real bodies. The Model Parliament (SPEC §11) and the multi-agent "
            "institutional reviewers (SPEC §18) reason over the same simulated "
            "evidence; prose may be LLM-polished but no institution generates a "
            "core number (SPEC §34)."
        ),
        parliament_agents=[
            "Government",
            "Opposition",
            "Equity",
            "Economist",
            "Devil's Advocate",
        ],
        institutional_agents=[
            "Climate",
            "Implementation",
            "Legal / Constitutional Research",
            "Auditor",
        ],
        not_modelled=[
            "real agency/council org structures & budgets",
            "enforcement capacity as a physical resource (assumed sufficient)",
        ],
    )


def _build_society() -> SocietyLayer:
    op = OpinionParams()
    priors = {band: op.prior_for(band) for band in _BAND_ORDER}

    # Structural, policy-independent role priors for the diffusion actors
    # (SPEC §14). These are baseline dispositions before any specific policy.
    actors = [
        SocietyActor(
            id="government", kind="politician", label="Government (proposer)", prior=0.7,
            rationale="A proposing government backs its own policy.",
        ),
        SocietyActor(
            id="opposition", kind="politician", label="Opposition", prior=-0.6,
            rationale="Opposition role stance (structural).",
        ),
        SocietyActor(
            id="business", kind="business", label="Business / commerce lobby", prior=-0.5,
            rationale="Business lobby is wary of new commuter/logistics charges.",
        ),
        SocietyActor(
            id="journalists", kind="journalist", label="Press / media", prior=0.0,
            rationale="Press starts neutral; editorial spread modelled in /media.",
        ),
        SocietyActor(
            id="community_groups", kind="community_group", label="Community / equity groups",
            prior=0.15, rationale="Community groups lean supportive if reinvestment/equity present.",
        ),
        SocietyActor(
            id="institutions", kind="institution", label="Public institutions / experts",
            prior=0.15, rationale="Expert institutions lean mildly evidence-positive.",
        ),
    ]

    return SocietyLayer(
        note=(
            "Society is modelled as aggregate cohorts + typed actors (SPEC §14). "
            "Opinion priors are small, transparent leans; the full support "
            "distribution is computed per policy by /public and diffused by "
            "/diffusion. Priors are Estimated assumptions, not measured data."
        ),
        opinion_priors_by_income_band=priors,
        media_environment=[
            "public-service broadcaster",
            "business press",
            "local paper",
            "tabloid",
            "environment desk",
            "opposition-aligned outlet",
        ],
        civic_actors=actors,
        not_modelled=[
            "individual-level political affiliation (only aggregate income-band "
            "leans, kept aggregate by design, SPEC §5)",
            "named real unions / associations (modelled as generic actor classes)",
        ],
    )


_BUILDERS = {
    "population": _build_population,
    "economy": _build_economy,
    "geography": _build_geography,
    "environment": _build_environment,
    "institutions": _build_institutions,
    "society": _build_society,
}


@lru_cache(maxsize=32)
def _compose(layers: tuple[str, ...]) -> WorldModel:
    kwargs = {name: _BUILDERS[name]() for name in layers}
    return WorldModel(
        layer_selection=(
            "SPEC §5 builds the smallest sufficient world model for the policy. "
            "A transport pricing / pedestrianisation policy activates all six "
            "layers (mobility→Population, commute cost→Economy, road network→"
            "Geography, emissions→Environment, governance→Institutions, opinion→"
            "Society). Request a subset with ?layers=population,geography."
        ),
        layers_returned=list(layers),
        **kwargs,
    )


def compose_world(layers: tuple[str, ...] | None = None) -> WorldModel:
    """Compose World A across the requested SPEC §5 layers (default: all six)."""
    selected = tuple(l for l in ALL_LAYERS if layers is None or l in layers)
    if not selected:
        selected = ALL_LAYERS
    return _compose(selected)


def clear_cache() -> None:
    """Drop the composition cache (used by tests after dataset regeneration)."""
    _compose.cache_clear()
