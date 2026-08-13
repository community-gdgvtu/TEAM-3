"""Named exogenous-shock catalogue for the stress-testing layer (SPEC §20).

SPEC §20 asks for a fixed set of scenario *toggles* — recession, fuel-price
spike, flood, heatwave, population growth, migration change, technology adoption,
interest-rate shock — so a user can ask "the policy performs well under baseline,
but does it fail under a recession + fuel shock?".

Each scenario here maps that named, human-meaningful shock onto the transparent
numeric knobs the deterministic mode-choice model already understands
(:class:`~app.simulation.shocks.Shocks`): a car running-cost multiplier, a
transit-fare multiplier, and the exogenous background-demand growth rate. The
mapping is deliberately explicit and auditable — no hidden randomness, no LLM
(SPEC §20/§34). Magnitudes are Estimated scenario inputs.

**Honesty about fidelity (SPEC §34).** This MVP engine is a static commuter
mode-choice model. Some shocks (fuel-price spike, background-demand shifts) it
represents directly and faithfully; others (a flood, a heatwave, an interest-rate
move) are transient or act through channels the mode-choice core does not carry.
Each scenario therefore declares a ``fidelity`` — ``modelled`` / ``partial`` /
``proxy`` — and a plain-language ``caveat`` so the stress result is never
over-sold. Weakly-represented shocks stay in the catalogue for completeness but
say so, rather than faking precision.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..simulation.shocks import Shocks

# Baseline exogenous demand-growth rate (``BaselineTrend.demand_growth_per_year``)
# that the demographic scenarios perturb *relative to*. Kept here as a documented
# reference so the rationale text stays truthful if the baseline is retuned.
_BASELINE_DEMAND_GROWTH = 0.015


@dataclass(frozen=True)
class ShockScenario:
    """One named, transparent exogenous scenario (SPEC §20)."""

    key: str
    label: str
    category: str  # macro | energy | climate | demographic | technology
    description: str
    overrides: Shocks
    rationale: str
    fidelity: str  # "modelled" | "partial" | "proxy"
    caveat: str

    def as_card(self) -> dict:
        """Serialisable description for the catalogue endpoint / Evidence Drawer."""
        return {
            "key": self.key,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "overrides": self.overrides.model_dump(),
            "rationale": self.rationale,
            "fidelity": self.fidelity,
            "caveat": self.caveat,
            "provenance": "Estimated",  # scenario assumption, not observed
        }


#: The SPEC §20 shock toggles, in a stable presentation order.
SHOCK_CATALOGUE: tuple[ShockScenario, ...] = (
    ShockScenario(
        key="recession",
        label="Recession",
        category="macro",
        description="A macroeconomic downturn: fewer trips, weaker travel demand.",
        overrides=Shocks(demand_growth_per_year=-0.010),
        rationale=(
            "Background commute demand contracts to −1.0%/yr (vs the +1.5%/yr "
            "baseline) as employment and discretionary travel fall."
        ),
        fidelity="partial",
        caveat=(
            "Only the aggregate demand contraction is modelled; income-specific "
            "effects (who stops commuting, how price sensitivity shifts) are not "
            "captured by the static mode-choice core."
        ),
    ),
    ShockScenario(
        key="fuel_price_spike",
        label="Fuel-price spike",
        category="energy",
        description="An energy-price shock that raises the cost of driving.",
        overrides=Shocks(car_cost_per_km_multiplier=1.5),
        rationale=(
            "Car running cost per km rises +50%, the primary channel of an energy "
            "shock. This is exactly the lever the mode-choice model consumes."
        ),
        fidelity="modelled",
        caveat=(
            "Represented directly and faithfully via car cost-per-km; assumes a "
            "sustained (not one-week) price level."
        ),
    ),
    ShockScenario(
        key="flood",
        label="Flood",
        category="climate",
        description="A flood degrading road access (detours, closures, slower roads).",
        overrides=Shocks(car_cost_per_km_multiplier=1.25),
        rationale=(
            "Proxied as a +25% effective driving-cost penalty standing in for "
            "detours and reduced road availability."
        ),
        fidelity="proxy",
        caveat=(
            "A flood is a transient, spatially-specific disruption; this static "
            "equilibrium model cannot time-resolve it or route around specific "
            "closed links (that needs the §7.7 spatial layer). Read as 'sustained "
            "degraded road access', not a dated event."
        ),
    ),
    ShockScenario(
        key="heatwave",
        label="Heatwave",
        category="climate",
        description="Extreme heat: hotter, more crowded transit nudges some to cars.",
        overrides=Shocks(car_cost_per_km_multiplier=1.05, transit_fare_multiplier=1.10),
        rationale=(
            "Proxied as a small comfort penalty on transit (a +10% fare-equivalent "
            "deterrent) and a slight +5% driving cost (AC/energy)."
        ),
        fidelity="proxy",
        caveat=(
            "Thermal comfort is not a variable in the mode-choice model; the fare "
            "multiplier is a crude stand-in for reduced transit attractiveness. "
            "Effect is intentionally small and low-confidence."
        ),
    ),
    ShockScenario(
        key="population_growth",
        label="Population growth",
        category="demographic",
        description="Faster population/employment growth lifting travel demand.",
        overrides=Shocks(demand_growth_per_year=0.035),
        rationale=(
            "Background commute demand grows +3.5%/yr (vs +1.5%/yr baseline), "
            "loading more trips onto the network and transit over the horizon."
        ),
        fidelity="modelled",
        caveat=(
            "Applied as a uniform growth uplift; no change to the spatial "
            "distribution of new residents/jobs."
        ),
    ),
    ShockScenario(
        key="migration_change",
        label="Migration change",
        category="demographic",
        description="Net in-migration raising demand above trend.",
        overrides=Shocks(demand_growth_per_year=0.025),
        rationale=(
            "Background demand grows +2.5%/yr, a milder demographic uplift than a "
            "full population-growth scenario."
        ),
        fidelity="partial",
        caveat=(
            "Modelled purely as extra aggregate demand; the demographic mix and "
            "where new residents live/work are not differentiated."
        ),
    ),
    ShockScenario(
        key="technology_adoption",
        label="Technology adoption",
        category="technology",
        description="EV uptake (cheaper per km) plus remote-work damping demand.",
        overrides=Shocks(car_cost_per_km_multiplier=0.80, demand_growth_per_year=0.008),
        rationale=(
            "EV adoption cuts car running cost per km −20%; remote/hybrid work "
            "damps background commute growth to +0.8%/yr."
        ),
        fidelity="partial",
        caveat=(
            "Cheaper EV driving is captured, but tailpipe CO₂ per km is held "
            "constant, so this scenario UNDER-states the emissions benefit of "
            "electrification (the emissions channel needs a separate fleet factor). "
            "Read the traffic/mode-share deltas, not CO₂, for this shock."
        ),
    ),
    ShockScenario(
        key="interest_rate_shock",
        label="Interest-rate shock",
        category="macro",
        description="Higher rates: pricier reinvestment financing, tighter budgets.",
        overrides=Shocks(demand_growth_per_year=0.005),
        rationale=(
            "Applied only as a mild demand damp (+0.5%/yr) standing in for tighter "
            "household budgets."
        ),
        fidelity="proxy",
        caveat=(
            "An interest-rate move acts mainly on the COST OF FINANCING the transit "
            "reinvestment programme and on household finances — channels the "
            "mode-choice core does not carry. Its real bite is in the §7.4 economy "
            "layer (POST /economy); here it is near-inert by design. Do not read a "
            "small mode-choice delta as the true fiscal impact."
        ),
    ),
)

_BY_KEY = {s.key: s for s in SHOCK_CATALOGUE}


def get_scenario(key: str) -> ShockScenario | None:
    """Return the named scenario, or ``None`` if the key is unknown."""
    return _BY_KEY.get(key)


def catalogue_keys() -> list[str]:
    """All valid scenario keys, in presentation order."""
    return [s.key for s in SHOCK_CATALOGUE]
