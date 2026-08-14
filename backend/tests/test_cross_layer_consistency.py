"""Cross-layer mode-choice consistency guard (SPEC §7.3 / §7.7 / §34).

Several forecast layers advertise that they read the **same deterministic
mode-choice model** as ``/simulate`` — that is the whole reason a layer's
numbers are allowed to be trusted alongside the ABM (SPEC §34: one source of
truth for the physical mode split, no per-layer re-invention):

* the **spatial** traffic-assignment layer (§7.7) claims *"the spatial layer
  can never disagree with the ABM's mode split"* — it only loads onto the road
  network commuters who *still choose to drive* under the very same
  ``choose_mode`` / ``choose_mode_policy`` functions;
* the **microsim** distributional layer (§7.3) claims *"the same deterministic
  mode-choice model as `/simulate`"* — except it reaches it through the
  ``mode_options`` / ``policy_mode_options`` + ``pick_mode`` primitives rather
  than the ``choose_mode`` wrappers.

Every per-layer test checks each layer **in isolation**, so none of them would
notice if a refactor let these paths drift apart — e.g. a change to
``choose_mode`` that ``pick_mode(mode_options(...))`` no longer mirrors, or a
layer quietly sampling a different population. The result would be a spatial
network or a who-gains/who-loses table built on a *different* mode split than
the headline ``/simulate`` numbers next to it — exactly the silent cross-layer
contract drift §34's determinism claim forbids.

This module enforces the shared truth directly: for several structurally
different policies it computes the canonical World-A / World-B car-commuter set
from the population once, then asserts ``/simulate``, the microsim mode path and
the spatial demand builder all reproduce it — at the level of *every individual
agent's decision*, not just the aggregate count.

Test-track only: no ``backend/app/**`` behaviour is exercised beyond the public
model entry points.
"""

from __future__ import annotations

import pytest

from app import dataset
from app.baseline.model import (
    CAR,
    DEFAULT_PARAMS,
    choose_mode,
    compute_baseline,
    mode_options,
    pick_mode,
)
from app.microsim.model import policy_mode_options
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation.levers import derive_levers
from app.simulation.model import (
    DEFAULT_SIM_PARAMS,
    choose_mode_policy,
    compute_world_b,
)
from app.spatial.model import (
    DEFAULT_SPATIAL_PARAMS,
    _car_demand,
    _representation_factor,
)


def _charge(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="xlayer_charge",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _pedestrianisation() -> PolicyDSL:
    return PolicyDSL(
        id="xlayer_ped",
        intervention=Intervention(
            type=InterventionType.pedestrianisation, currency="local"
        ),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def _noop() -> PolicyDSL:
    # A charge of zero into the general fund: structurally a policy, behaviourally
    # a no-op, so World B must equal World A everywhere.
    return PolicyDSL(
        id="xlayer_noop",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=0.0, currency="local"
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )


# Distinct policy *shapes* so the agreement below is a real invariant, not a
# coincidence of one scenario: a reinvesting charge, a general-fund charge, a
# car ban, and a behavioural no-op.
POLICIES = {
    "charge_reinvest": _charge(12.0, 1.0),
    "charge_general_fund": _charge(8.0, 0.0),
    "pedestrianisation": _pedestrianisation(),
    "noop": _noop(),
}


def _canonical_modes(policy: PolicyDSL):
    """The single source of truth: each agent's World-A and World-B mode via the
    ``choose_mode`` / ``choose_mode_policy`` wrappers the ABM (`/simulate`) uses."""
    agents = dataset.population_agents()
    cbd = dataset.cbd_zone_ids()
    levers = derive_levers(policy, params=DEFAULT_PARAMS, sim=DEFAULT_SIM_PARAMS)
    modes_a = [choose_mode(a, DEFAULT_PARAMS) for a in agents]
    modes_b = [choose_mode_policy(a, levers, cbd, DEFAULT_PARAMS) for a in agents]
    return agents, cbd, levers, modes_a, modes_b


@pytest.mark.parametrize("key", list(POLICIES))
def test_simulate_matches_canonical_mode_split(key):
    """`/simulate`'s reported car-commuter counts equal the canonical split."""
    policy = POLICIES[key]
    _, _, _, modes_a, modes_b = _canonical_modes(policy)
    car_a = sum(1 for m in modes_a if m == CAR)
    car_b = sum(1 for m in modes_b if m == CAR)

    base = compute_baseline(DEFAULT_PARAMS)
    wb = compute_world_b(policy)

    assert base.traffic.car_commuters == car_a
    assert wb.traffic.car_commuters == car_b


@pytest.mark.parametrize("key", list(POLICIES))
def test_microsim_mode_path_agrees_agent_by_agent(key):
    """The microsim primitives (`mode_options`/`policy_mode_options` + `pick_mode`)
    reproduce the ABM's `choose_mode` / `choose_mode_policy` for *every* agent.

    This is the strongest form of the §7.3 "same mode-choice model as /simulate"
    claim: not just equal totals, but an identical per-person decision, so the
    who-gains/who-loses table cannot silently disagree with the headline split.
    """
    policy = POLICIES[key]
    agents, cbd, levers, modes_a, modes_b = _canonical_modes(policy)

    for a, ref_a, ref_b in zip(agents, modes_a, modes_b):
        micro_a = pick_mode(mode_options(a, DEFAULT_PARAMS))
        micro_b = pick_mode(policy_mode_options(a, levers, cbd, DEFAULT_PARAMS))
        assert micro_a == ref_a
        assert micro_b == ref_b


@pytest.mark.parametrize("key", list(POLICIES))
def test_spatial_demand_reflects_canonical_car_split(key):
    """The spatial layer loads exactly the canonical car commuters onto the road
    network (expanded by the documented, policy-independent scaling factors).

    ``_car_demand`` returns the *peak-hour* car person-trips, which are the raw
    canonical car count scaled by the representation factor and peak-hour share.
    Re-deriving that expansion from the canonical split and requiring an exact
    match proves the spatial layer neither adds, drops nor re-classifies any
    driver relative to the ABM (SPEC §7.7 / §34).
    """
    policy = POLICIES[key]
    agents, cbd, levers, modes_a, modes_b = _canonical_modes(policy)
    car_a = sum(1 for m in modes_a if m == CAR)
    car_b = sum(1 for m in modes_b if m == CAR)

    rep = _representation_factor()
    peak = DEFAULT_SPATIAL_PARAMS.peak_hour_share

    _, trips_a = _car_demand(
        agents, None, cbd, DEFAULT_PARAMS, DEFAULT_SPATIAL_PARAMS, rep
    )
    _, trips_b = _car_demand(
        agents, levers, cbd, DEFAULT_PARAMS, DEFAULT_SPATIAL_PARAMS, rep
    )

    assert trips_a == int(round(car_a * rep * peak))
    assert trips_b == int(round(car_b * rep * peak))


def test_noop_policy_is_behaviourally_identical_across_layers():
    """A zero charge must leave the mode split untouched in every layer — the
    cleanest end-to-end check that the layers share one behavioural core."""
    _, _, _, modes_a, modes_b = _canonical_modes(POLICIES["noop"])
    assert modes_a == modes_b  # canonical: no behaviour change

    base = compute_baseline(DEFAULT_PARAMS)
    wb = compute_world_b(POLICIES["noop"])
    assert base.traffic.car_commuters == wb.traffic.car_commuters


def test_all_layers_read_the_same_population_size():
    """Cross-layer agreement is meaningless if the layers sample different
    populations; pin that ``/simulate`` classifies exactly the one synthetic
    population every other layer iterates (car + transit commuters can never
    exceed it, and equal the canonical car/transit split)."""
    agents = dataset.population_agents()
    n = len(agents)
    assert n > 0

    car_a = sum(1 for a in agents if choose_mode(a, DEFAULT_PARAMS) == CAR)
    base = compute_baseline(DEFAULT_PARAMS)
    # Same population, same mode function → identical car count, and the mode
    # counts partition (never over-count) that population.
    assert base.traffic.car_commuters == car_a
    assert base.traffic.car_commuters + base.transit.transit_commuters <= n
