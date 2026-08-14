"""Curated database of real-world congestion-pricing / access-restriction schemes.

These are the historical analogues SPEC §7.1 wants the causal layer to reason
from. Every figure here is an **illustrative, approximate published value** for a
real scheme — assembled for the prototype, not read from a live dataset and not
this city's data. They are tagged Observed (they describe real interventions) but
each carries a ``source_note`` flagging the approximation, and the *transfer* of
these effects to a new policy is Estimated (see ``model.py``). No LLM produced any
of these numbers; they are fixed, auditable constants a human can correct.

``charge_strength`` is a deliberately coarse 0–3 bucket (none / low / moderate /
high) rather than a cross-currency amount, because comparing £5, €5, SEK 60 and
S$ tolls on an absolute scale would be false precision. The bucket is Estimated.
"""

from __future__ import annotations

from .schema import HistoricalCase

# Coarse charge-strength buckets (currency-agnostic; Estimated judgement).
CHARGE_NONE = 0
CHARGE_LOW = 1
CHARGE_MODERATE = 2
CHARGE_HIGH = 3

# Bucket → the strength label used in prose.
CHARGE_STRENGTH_LABEL = {0: "none", 1: "low", 2: "moderate", 3: "high"}

# Documented per-case charge strength (see docstring — coarse, Estimated).
_CHARGE_STRENGTH = {
    "london_ccz": CHARGE_MODERATE,
    "stockholm_tax": CHARGE_MODERATE,
    "singapore_erp": CHARGE_HIGH,
    "milan_area_c": CHARGE_MODERATE,
    "gothenburg_tax": CHARGE_LOW,
    "oslo_toll_ring": CHARGE_LOW,
    "ghent_circulation": CHARGE_NONE,
    "madrid_central": CHARGE_NONE,
}


CASES: list[HistoricalCase] = [
    HistoricalCase(
        id="london_ccz",
        name="London Congestion Charge",
        city="London",
        country="United Kingdom",
        year=2003,
        intervention_family="road_pricing",
        scheme="Flat daily charge to drive within a central cordon (07:00–18:00).",
        treated_change_pct=-18.0,  # traffic entering the charged zone, year 1
        control_change_pct=1.0,  # background/outer-London trend
        charge_per_day_ref=5.0,  # £5 introductory daily charge
        reinvested_in_transit=True,
        design="Pre/post monitoring with outer-London comparison (event-study style).",
        identification_strength=0.70,
        parallel_trend_note=(
            "Fuel price and the economic cycle are confounders; an outer-London "
            "comparison arm partly controls for city-wide trends but is imperfect."
        ),
        context_similarity=0.75,
        mode_shift_note="Most displaced car trips shifted to bus and rail; some rerouted around the cordon.",
    ),
    HistoricalCase(
        id="stockholm_tax",
        name="Stockholm Congestion Tax",
        city="Stockholm",
        country="Sweden",
        year=2007,
        intervention_family="road_pricing",
        scheme="Time-varying cordon toll on crossings into the inner city.",
        treated_change_pct=-22.0,  # cordon crossings vs pre-trial
        control_change_pct=0.0,
        charge_per_day_ref=60.0,  # ~SEK per typical day (time-varying)
        reinvested_in_transit=True,
        design="2006 trial → 2007 referendum → permanent: a strong natural experiment.",
        identification_strength=0.85,
        parallel_trend_note=(
            "The on/off trial and referendum give unusually clean before/after "
            "identification; residual seasonal and weather effects remain."
        ),
        context_similarity=0.70,
        mode_shift_note="Large shift to an already strong public-transport network.",
    ),
    HistoricalCase(
        id="singapore_erp",
        name="Singapore Area Licensing → Electronic Road Pricing",
        city="Singapore",
        country="Singapore",
        year=1998,
        intervention_family="road_pricing",
        scheme="Area licence (1975) then per-gantry electronic road pricing into the CBD.",
        treated_change_pct=-44.0,  # restricted-zone traffic on ALS introduction
        control_change_pct=-2.0,
        charge_per_day_ref=6.0,  # illustrative daily equivalent
        reinvested_in_transit=False,
        design="Strong pre/post on introduction; weak modern control arm.",
        identification_strength=0.60,
        parallel_trend_note=(
            "The 1975 effect is large but old, bundled with parking and vehicle-"
            "ownership policy, in a very different governance context."
        ),
        context_similarity=0.45,
        mode_shift_note="Shift to buses and car-pooling; strong complementary ownership taxes.",
    ),
    HistoricalCase(
        id="milan_area_c",
        name="Milan Area C",
        city="Milan",
        country="Italy",
        year=2012,
        intervention_family="road_pricing",
        scheme="Central cordon charge combined with a low-emission-zone access rule.",
        treated_change_pct=-30.0,  # entering traffic
        control_change_pct=-3.0,  # recession-era background decline
        charge_per_day_ref=5.0,  # €5 daily
        reinvested_in_transit=True,
        design="Referendum mandate + monitoring; a court suspension created a natural on/off.",
        identification_strength=0.70,
        parallel_trend_note=(
            "Introduced during a recession; the background-decline control arm "
            "matters, and the charge is bundled with an emissions rule."
        ),
        context_similarity=0.70,
        mode_shift_note="Shift to transit and cleaner vehicles; revenue funded sustainable mobility.",
    ),
    HistoricalCase(
        id="gothenburg_tax",
        name="Gothenburg Congestion Tax",
        city="Gothenburg",
        country="Sweden",
        year=2013,
        intervention_family="road_pricing",
        scheme="Cordon toll modelled on Stockholm, in a smaller, more car-dependent city.",
        treated_change_pct=-12.0,
        control_change_pct=-1.0,
        charge_per_day_ref=30.0,  # ~SEK, lower than Stockholm
        reinvested_in_transit=False,
        design="DiD vs comparison cities; a referendum opposed it after introduction.",
        identification_strength=0.70,
        parallel_trend_note=(
            "Smaller, more car-dependent city with weaker transit alternatives — "
            "the effect is genuinely smaller, not just noisier."
        ),
        context_similarity=0.65,
        mode_shift_note="Modest shift; more rerouting and trip suppression than in Stockholm.",
    ),
    HistoricalCase(
        id="oslo_toll_ring",
        name="Oslo Toll Ring",
        city="Oslo",
        country="Norway",
        year=1990,
        intervention_family="road_pricing",
        scheme="Long-standing toll ring, revenue split between transit and road investment.",
        treated_change_pct=-5.0,  # incremental per-stage effect on ring crossings
        control_change_pct=0.0,
        charge_per_day_ref=40.0,  # ~NOK per crossing, illustrative
        reinvested_in_transit=True,
        design="Long time series across toll changes; effect estimated per uplift.",
        identification_strength=0.60,
        parallel_trend_note=(
            "Originally a revenue-raising ring, not a demand-management cordon, so "
            "per-stage traffic effects are small and hard to isolate from growth."
        ),
        context_similarity=0.70,
        mode_shift_note="Modest; toll long treated as a financing tool more than a deterrent.",
    ),
    HistoricalCase(
        id="ghent_circulation",
        name="Ghent Circulation Plan",
        city="Ghent",
        country="Belgium",
        year=2017,
        intervention_family="pedestrianisation",
        scheme="City-centre car-circulation plan: through-traffic removed via sectors + a car-free core.",
        treated_change_pct=-25.0,  # central car traffic
        control_change_pct=0.0,
        charge_per_day_ref=None,
        reinvested_in_transit=False,
        design="Pre/post monitoring of central car counts and cycling.",
        identification_strength=0.55,
        parallel_trend_note=(
            "No charge, so no price identification; effect is engineering-driven "
            "rerouting. Displacement to the ring road is a key confounder."
        ),
        context_similarity=0.70,
        mode_shift_note="Large shift to cycling and walking; some displacement to the ring road.",
    ),
    HistoricalCase(
        id="madrid_central",
        name="Madrid Central low-emission zone",
        city="Madrid",
        country="Spain",
        year=2018,
        intervention_family="low_emission_zone",
        scheme="Central access restriction by vehicle emissions class (an LEZ, not a charge).",
        treated_change_pct=-24.0,  # traffic in the restricted zone
        control_change_pct=-1.0,
        charge_per_day_ref=None,
        reinvested_in_transit=False,
        design="Pre/post; a political reversal then reinstatement created a natural on/off.",
        identification_strength=0.60,
        parallel_trend_note=(
            "Access rule, not a price; the brief 2019 suspension aids identification "
            "but confounds with seasonal and enforcement changes."
        ),
        context_similarity=0.70,
        mode_shift_note="Shift to compliant vehicles and transit; NO₂ fell inside the zone.",
    ),
]

CASES_BY_ID = {c.id: c for c in CASES}


def charge_strength(case_id: str) -> int:
    """Coarse 0–3 charge-strength bucket for a case (Estimated; see module docstring)."""
    return _CHARGE_STRENGTH.get(case_id, CHARGE_NONE)
