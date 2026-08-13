"""Translate a compiled Policy DSL into concrete numeric mode-choice levers.

This is the bridge between the *structured policy* (SPEC §3, produced by the
compiler) and the *numeric model* (SPEC §7.5 agent-based mode choice). It is
deliberately transparent and rule-based:

* No LLM is involved (SPEC §34) — a policy field maps to a model parameter by an
  explicit, auditable rule.
* Every derived lever is emitted as a :class:`BehaviouralRule` carrying its
  value, plausible range, sensitivity and source, satisfying the SPEC §7.5
  requirement that each behavioural rule be self-describing.

Supported levers for the demo slice (*price / pedestrianise a central district
and reinvest revenue into public transport*):

1. **Cordon charge** — a per-commuter surcharge on CBD-bound car trips
   (road-pricing / parking-levy interventions).
2. **Pedestrianisation** — cars are banned from the CBD, so CBD-bound commuters
   lose the car option entirely.
3. **Transit reinvestment** — revenue allocated to public transport buys a
   bounded fare cut and service-speed uplift, which pulls commuters toward
   transit. Only engaged when the policy actually allocates revenue there.
4. **Low-emission zone** — modelled by its *real* mechanism rather than as a flat
   cordon charge: only the *non-compliant* share of the car fleet faces the daily
   charge (so the mode-shift pressure is a fraction of an equivalent congestion
   charge), and the zone's primary effect is fleet turnover toward cleaner
   vehicles, which lowers World B's CO₂-per-km factor. This makes an LEZ behave
   distinctly from a congestion charge — a modest traffic effect but a real
   emissions-intensity cut — instead of aliasing to the same numbers.
5. **Workplace parking levy** — also distinct from a flat cordon charge: it is
   levied on the *employer* per parking space, who passes only a fraction through
   to the commuter, so its behavioural signal (and mode shift) is proportionately
   smaller than an equivalent road-pricing charge. Unlike an LEZ it does not clean
   the fleet — it cuts emissions purely by cutting car-km.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..policy.dsl import InterventionType, PolicyDSL
from .schema import BehaviouralRule

# Intervention families that levy a flat per-entry charge on *every* car entering
# the cordon. A low-emission zone is deliberately NOT here — it charges only
# non-compliant vehicles and its main lever is a cleaner fleet. A parking levy is
# NOT here either — it is charged to the employer per parking space and only
# partially passed through to the commuter, so its behavioural signal is a
# fraction of a flat cordon charge. Both get their own branch in
# :func:`derive_levers` rather than aliasing to the same numbers as road pricing.
_PRICING_TYPES = {
    InterventionType.road_pricing,
}

# Exemption phrases we can currently model against agent attributes. Anything we
# cannot map stays visible in the DSL but does not silently alter numbers.
_RESIDENT_HINTS = ("resident", "residents")
_LOW_INCOME_HINTS = ("low-income", "low income", "low_income")
_DISABLED_HINTS = ("disabled", "disability", "blue badge", "blue-badge")


@dataclass(frozen=True)
class SimParams:
    """World-B modelling assumptions (kept separate so World A is untouched).

    All are transparent input assumptions surfaced for the Evidence Drawer.
    """

    #: A daily cordon charge is amortised across the commuter's daily trips so it
    #: is comparable with the baseline's per-one-way generalized cost.
    charge_trips_per_day: int = DEFAULT_PARAMS.trips_per_commuter_per_day
    #: Max transit fare cut at 100% revenue reinvestment (relative).
    reinvest_max_fare_cut: float = 0.30
    #: Max transit effective-speed uplift at 100% revenue reinvestment (relative).
    reinvest_max_speed_gain: float = 0.15
    #: Low-emission-zone: share of the CBD-bound car fleet that is non-compliant
    #: at introduction — only these vehicles face the LEZ charge (Estimated).
    lez_noncompliant_share: float = 0.25
    #: Low-emission-zone: CO₂-per-km of a compliant replacement vehicle as a
    #: fraction of the baseline fleet-average factor (newer/hybrid/EV mix). This
    #: is a CO₂ proxy for the tailpipe (NOx/PM) turnover an LEZ actually targets,
    #: so the CO₂ cut is deliberately modest, not dramatic (Estimated).
    lez_clean_factor_ratio: float = 0.40
    #: Workplace parking levy: share of the nominal levy that reaches the
    #: commuter as a behavioural signal. A WPL is charged to the *employer* per
    #: parking space (e.g. Nottingham's WPL); employers absorb some and pass the
    #: rest on, so only a fraction lands as a per-commuter cost — the mode-shift
    #: pressure is proportionately smaller than an equivalent flat cordon charge
    #: that every entering vehicle pays in full (Estimated).
    parking_levy_passthrough_share: float = 0.55

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_SIM_PARAMS = SimParams()


@dataclass
class PolicyLevers:
    """Concrete numeric levers derived from a Policy DSL for one simulation run."""

    #: Per-one-way-trip car surcharge for non-exempt CBD-bound commuters (currency).
    charge_per_one_way: float = 0.0
    #: Whether cars are banned from the CBD (pedestrianisation).
    car_banned_in_cbd: bool = False
    #: Multiplier applied to the transit fare (<= 1 means cheaper).
    transit_fare_multiplier: float = 1.0
    #: Multiplier applied to transit effective speed (>= 1 means faster).
    transit_speed_multiplier: float = 1.0
    #: Multiplier applied to World B's car CO₂-per-km factor (<= 1 means a cleaner
    #: fleet). Only a low-emission zone moves this off 1.0 — every other policy
    #: cuts emissions purely by cutting vehicle-km, so World A and World B share
    #: the same emissions factor and existing numbers are unchanged.
    co2_factor_multiplier: float = 1.0
    #: Exemption flags we could map to agent attributes.
    exempt_residents: bool = False
    exempt_low_income: bool = False
    exempt_disabled: bool = False
    #: Behavioural-rule audit records (SPEC §7.5) for every engaged lever.
    rules: list[BehaviouralRule] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("rules", None)
        return d

    def is_exempt(self, agent: dict, cbd_zone_ids: set[str]) -> bool:
        """Whether ``agent`` is exempt from the cordon charge under this policy."""
        if self.exempt_residents and agent.get("home_zone") in cbd_zone_ids:
            return True
        if self.exempt_low_income and agent.get("income_band") == "low":
            return True
        # ``disabled`` is not a synthetic-population attribute, so it cannot alter
        # numbers here; it remains visible in the DSL/behavioural rules only.
        return False


def _match_exemptions(exemptions: list[str]) -> tuple[bool, bool, bool]:
    """Return (residents, low_income, disabled) exemption flags from free text."""
    joined = " ".join(exemptions).lower()
    residents = any(h in joined for h in _RESIDENT_HINTS)
    low_income = any(h in joined for h in _LOW_INCOME_HINTS)
    disabled = any(h in joined for h in _DISABLED_HINTS)
    return residents, low_income, disabled


def derive_levers(
    policy: PolicyDSL,
    params: BaselineParams = DEFAULT_PARAMS,
    sim: SimParams = DEFAULT_SIM_PARAMS,
) -> PolicyLevers:
    """Map a compiled :class:`PolicyDSL` to concrete numeric mode-choice levers.

    The mapping is deterministic and auditable (SPEC §34). Each engaged lever
    also records a :class:`BehaviouralRule` with its range and sensitivity so the
    Evidence Drawer can explain exactly how the policy became numbers (SPEC §7.5).
    """
    levers = PolicyLevers()
    itype = policy.intervention.type
    residents, low_income, disabled = _match_exemptions(policy.exemptions)
    levers.exempt_residents = residents
    levers.exempt_low_income = low_income
    levers.exempt_disabled = disabled

    # --- 1. Cordon charge (pricing interventions) --------------------------
    amount = policy.intervention.amount
    if itype in _PRICING_TYPES and amount and amount > 0:
        per_one_way = amount / max(1, sim.charge_trips_per_day)
        levers.charge_per_one_way = per_one_way
        levers.rules.append(
            BehaviouralRule(
                name="cordon_charge",
                label="Cordon charge on CBD-bound cars",
                parameter="Currency added to car generalized cost per one-way CBD-bound trip",
                value=round(per_one_way, 4),
                unit=policy.intervention.currency,
                plausible_range=[0.0, amount],
                sensitivity=(
                    "Higher charge shifts more price-sensitive car commuters to "
                    "transit/walk; low-income agents (higher price_sensitivity) "
                    "respond most."
                ),
                source=(
                    f"intervention.amount ({amount} {policy.intervention.currency}) "
                    f"amortised over {sim.charge_trips_per_day} daily trips"
                ),
            )
        )

    # --- 2. Pedestrianisation (car ban in the cordon) ----------------------
    if itype == InterventionType.pedestrianisation:
        levers.car_banned_in_cbd = True
        levers.rules.append(
            BehaviouralRule(
                name="pedestrianisation",
                label="Cars banned from the central district",
                parameter="Car option removed for CBD-bound commuters",
                value=1.0,
                unit="bool",
                plausible_range=[0.0, 1.0],
                sensitivity=(
                    "All CBD-bound car commuters must switch to transit or walk; "
                    "the strongest lever on central traffic and emissions."
                ),
                source="intervention.type == pedestrianisation",
            )
        )

    # --- 2b. Low-emission zone (compliance-based charge + fleet cleanup) ----
    # An LEZ is NOT a flat cordon charge. Only the non-compliant share of the
    # fleet pays, so the mode-shift pressure is a fraction of an equivalent
    # congestion charge; and the zone's primary lever is fleet turnover toward
    # cleaner vehicles, which lowers the CO₂-per-km factor in World B only.
    if itype == InterventionType.low_emission_zone and amount and amount > 0:
        share = max(0.0, min(1.0, sim.lez_noncompliant_share))
        # Fleet-expected charge: amortise the daily amount over trips, then scale
        # by the non-compliant share (compliant vehicles pay nothing). This
        # conserves total charge revenue (share of the fleet × full charge) while
        # applying a proportionately smaller behavioural signal to each commuter.
        per_one_way = (amount / max(1, sim.charge_trips_per_day)) * share
        levers.charge_per_one_way = per_one_way
        levers.rules.append(
            BehaviouralRule(
                name="lez_charge",
                label="Low-emission-zone charge on non-compliant cars",
                parameter="Fleet-expected currency added to car generalized cost per one-way CBD-bound trip",
                value=round(per_one_way, 4),
                unit=policy.intervention.currency,
                plausible_range=[0.0, amount / max(1, sim.charge_trips_per_day)],
                sensitivity=(
                    f"Only the ~{share:.0%} non-compliant share of the fleet pays, so "
                    "the mode-shift is a fraction of an equivalent flat congestion "
                    "charge; compliant drivers keep driving (cleaner vehicles)."
                ),
                source=(
                    f"intervention.amount ({amount} {policy.intervention.currency}) "
                    f"amortised over {sim.charge_trips_per_day} daily trips × "
                    f"{share:.2f} non-compliant share"
                ),
            )
        )
        # Fleet cleanup: the compliant share keeps the baseline factor; the
        # non-compliant share is replaced by cleaner vehicles emitting
        # ``lez_clean_factor_ratio`` of it → a blended World-B CO₂-per-km factor.
        clean = max(0.0, min(1.0, sim.lez_clean_factor_ratio))
        levers.co2_factor_multiplier = (1.0 - share) + share * clean
        levers.rules.append(
            BehaviouralRule(
                name="lez_fleet_cleanup",
                label="Cleaner vehicle fleet inside the low-emission zone",
                parameter="Multiplier on the car CO₂-per-km factor in World B",
                value=round(levers.co2_factor_multiplier, 4),
                unit="× baseline factor",
                plausible_range=[clean, 1.0],
                sensitivity=(
                    "The dominant LEZ lever: non-compliant vehicles are replaced by "
                    "cleaner ones, cutting emissions intensity even for drivers who "
                    "keep driving. Modelled as a CO₂ proxy for the tailpipe (NOx/PM) "
                    "turnover an LEZ targets, so the CO₂ cut is modest, not dramatic."
                ),
                source=(
                    f"(1 − {share:.2f} non-compliant) + {share:.2f} × "
                    f"{clean:.2f} clean-vehicle factor ratio"
                ),
            )
        )

    # --- 2c. Workplace parking levy (employer-charged, partial pass-through) -
    # A parking levy is NOT a flat cordon charge. It is levied on the employer per
    # parking space; employers absorb some of it and pass the rest to the
    # commuter, so only ``parking_levy_passthrough_share`` of the nominal amount
    # lands as a per-commuter behavioural signal → a proportionately smaller mode
    # shift than an equivalent road-pricing cordon that every vehicle pays in
    # full. It cuts emissions purely by cutting car-km (co2 factor stays 1.0),
    # which is what distinguishes it from a low-emission zone.
    if itype == InterventionType.parking_levy and amount and amount > 0:
        passthrough = max(0.0, min(1.0, sim.parking_levy_passthrough_share))
        per_one_way = (amount / max(1, sim.charge_trips_per_day)) * passthrough
        levers.charge_per_one_way = per_one_way
        levers.rules.append(
            BehaviouralRule(
                name="parking_levy_charge",
                label="Workplace parking levy passed through to commuters",
                parameter="Currency added to car generalized cost per one-way CBD-bound trip",
                value=round(per_one_way, 4),
                unit=policy.intervention.currency,
                plausible_range=[0.0, amount / max(1, sim.charge_trips_per_day)],
                sensitivity=(
                    f"Only the ~{passthrough:.0%} of the levy employers pass on reaches "
                    "the commuter, so the mode shift is a fraction of an equivalent "
                    "flat cordon charge; employers absorbing more weakens the signal."
                ),
                source=(
                    f"intervention.amount ({amount} {policy.intervention.currency}) "
                    f"amortised over {sim.charge_trips_per_day} daily trips × "
                    f"{passthrough:.2f} employer pass-through share"
                ),
            )
        )

    # --- 3. Transit reinvestment (revenue → better service) ----------------
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)
    pt_share = max(0.0, min(1.0, pt_share))
    if pt_share > 0.0 and (levers.charge_per_one_way > 0 or levers.car_banned_in_cbd):
        fare_mult = 1.0 - pt_share * sim.reinvest_max_fare_cut
        speed_mult = 1.0 + pt_share * sim.reinvest_max_speed_gain
        levers.transit_fare_multiplier = fare_mult
        levers.transit_speed_multiplier = speed_mult
        levers.rules.append(
            BehaviouralRule(
                name="transit_reinvestment",
                label="Revenue reinvested in public transport",
                parameter="Transit fare ×mult and effective-speed ×mult from reinvestment",
                value=round(pt_share, 3),
                unit="revenue share",
                plausible_range=[0.0, 1.0],
                sensitivity=(
                    f"At this {pt_share:.0%} reinvestment: fare ×{fare_mult:.2f}, "
                    f"speed ×{speed_mult:.2f}. Cheaper/faster transit pulls more "
                    "commuters off cars, compounding the charge/ban."
                ),
                source=(
                    "revenue_allocation.public_transport × sim reinvestment "
                    "service-gain assumptions"
                ),
            )
        )

    return levers
