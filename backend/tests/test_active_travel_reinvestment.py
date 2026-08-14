"""Active-travel revenue reinvestment (SPEC §7.5/§9/§34).

``revenue_allocation.active_travel`` is a first-class field on the Policy DSL —
parsed by the LLM/rule compiler and normalised by the compiler — but until now it
never touched a single number: a policy that spent all of its charge revenue on
protected cycle lanes and pavements produced byte-identical traffic/emissions to
one that banked the money in the general fund. That is dishonest (SPEC §34): it
would tell a minister that building active-travel infrastructure does nothing.

These tests pin the honest behaviour now that the share drives a real lever — an
``active_travel_speed_multiplier`` that scales both the effective active-travel
speed and the maximum walkable/cyclable commute distance in World B, pulling the
nearest-margin short-trip car and transit commuters onto foot/bike. Like transit
reinvestment it only engages when the charge/ban actually raises revenue, rides
the same reinvestment gate so it ramps in over the horizon (SPEC §9), and never
moves an existing (active-travel-free) policy's numbers.
"""

from __future__ import annotations

from app.policy.dsl import Intervention, InterventionType, PolicyDSL, RevenueAllocation
from app.policy.rules import parse_policy
from app.registry.model import build_registry
from app.simulation.levers import DEFAULT_SIM_PARAMS, derive_levers
from app.simulation.model import compute_world_b


def _charge_policy(alloc: RevenueAllocation) -> PolicyDSL:
    return PolicyDSL(
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=10.0, currency="GBP"
        ),
        revenue_allocation=alloc,
    )


# --- lever derivation ---------------------------------------------------------

def test_no_allocation_leaves_active_travel_untouched_regression() -> None:
    # The default (no active-travel spend) keeps the multiplier at 1.0 and emits
    # no active-travel rule, so every existing policy's numbers are unchanged.
    lev = derive_levers(_charge_policy(RevenueAllocation(general_fund=1.0)))
    assert lev.active_travel_speed_multiplier == 1.0
    assert not any(r.name == "active_travel_reinvestment" for r in lev.rules)


def test_allocation_scales_the_multiplier() -> None:
    full = derive_levers(_charge_policy(RevenueAllocation(active_travel=1.0)))
    half = derive_levers(_charge_policy(RevenueAllocation(active_travel=0.5)))
    g = DEFAULT_SIM_PARAMS.active_travel_max_speed_gain
    assert abs(full.active_travel_speed_multiplier - (1.0 + g)) < 1e-12
    assert abs(half.active_travel_speed_multiplier - (1.0 + 0.5 * g)) < 1e-12
    # And a rule is surfaced for the Evidence Drawer only when it bites.
    rule = next(r for r in full.rules if r.name == "active_travel_reinvestment")
    assert rule.plausible_range == [1.0, 1.0 + g]


def test_no_engagement_without_revenue() -> None:
    # An active-travel allocation with no charge and no ban has no revenue to
    # spend, so it must NOT invent a mode shift (same gate as transit reinvestment).
    p = PolicyDSL(
        intervention=Intervention(type=InterventionType.transit_investment),
        revenue_allocation=RevenueAllocation(active_travel=1.0),
    )
    lev = derive_levers(p)
    assert lev.active_travel_speed_multiplier == 1.0
    assert not any(r.name == "active_travel_reinvestment" for r in lev.rules)


def test_share_is_clamped_to_unit_interval() -> None:
    over = derive_levers(_charge_policy(RevenueAllocation(active_travel=5.0)))
    g = DEFAULT_SIM_PARAMS.active_travel_max_speed_gain
    assert abs(over.active_travel_speed_multiplier - (1.0 + g)) < 1e-12


# --- numeric effect on World B ------------------------------------------------

def test_active_travel_spend_shifts_commuters_onto_foot_and_bike() -> None:
    # Same £10 charge, revenue banked vs fully reinvested in active travel.
    banked = compute_world_b(
        _charge_policy(RevenueAllocation(general_fund=1.0)), reinvestment=True
    )
    active = compute_world_b(
        _charge_policy(RevenueAllocation(active_travel=1.0)), reinvestment=True
    )
    # Better/faster/wider-reach active travel pulls commuters off cars onto foot.
    assert active.mode_share.walk > banked.mode_share.walk
    assert active.mode_share.car < banked.mode_share.car
    # Fewer car-km ⇒ lower traffic and (via the shared factor) emissions.
    assert active.traffic.daily_vehicle_km < banked.traffic.daily_vehicle_km


def test_larger_allocation_shifts_more() -> None:
    half = compute_world_b(
        _charge_policy(RevenueAllocation(active_travel=0.5)), reinvestment=True
    )
    full = compute_world_b(
        _charge_policy(RevenueAllocation(active_travel=1.0)), reinvestment=True
    )
    assert full.mode_share.walk >= half.mode_share.walk
    assert full.mode_share.car <= half.mode_share.car


def test_short_run_anchor_is_neutral_so_it_ramps_in() -> None:
    # The infrastructure has not been built yet in the short-run anchor, so the
    # reinvestment-off World B is identical whether or not revenue is earmarked
    # for active travel — the uplift ramps in over the Time Machine horizon (§9).
    banked = compute_world_b(
        _charge_policy(RevenueAllocation(general_fund=1.0)), reinvestment=False
    )
    active = compute_world_b(
        _charge_policy(RevenueAllocation(active_travel=1.0)), reinvestment=False
    )
    assert active.mode_share.walk == banked.mode_share.walk
    assert active.mode_share.car == banked.mode_share.car


def test_transit_and_active_travel_reinvestment_coexist() -> None:
    # A split allocation engages both service levers independently.
    split = derive_levers(
        _charge_policy(RevenueAllocation(public_transport=0.6, active_travel=0.4))
    )
    names = {r.name for r in split.rules}
    assert "transit_reinvestment" in names
    assert "active_travel_reinvestment" in names
    assert split.transit_speed_multiplier > 1.0
    assert split.active_travel_speed_multiplier > 1.0


# --- rule compiler reachability ----------------------------------------------

def test_rule_compiler_extracts_active_travel_allocation() -> None:
    dsl, _ = parse_policy(
        "Charge £10 to drive into the centre and spend 40% of the revenue on "
        "protected cycle lanes and wider pavements."
    )
    assert dsl.revenue_allocation.active_travel == 0.4
    assert dsl.revenue_allocation.public_transport == 0.0


def test_transit_allocation_still_wins_when_both_mentioned() -> None:
    # Transit is matched first, so a transit-percentage still routes to transit.
    dsl, _ = parse_policy("Charge £10 and reinvest 70% of the revenue in buses.")
    assert dsl.revenue_allocation.public_transport == 0.7
    assert dsl.revenue_allocation.active_travel == 0.0


# --- registry transparency ----------------------------------------------------

def test_active_travel_gain_is_published_in_the_registry() -> None:
    reg = build_registry()
    index = {a.name: a.value for a in reg.assumption_index}
    assert (
        index["active_travel_max_speed_gain"]
        == DEFAULT_SIM_PARAMS.active_travel_max_speed_gain
    )
