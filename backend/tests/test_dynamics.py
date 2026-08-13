"""Tests for the System Dynamics / recursive-feedback layer (SPEC §7.6 + §19)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.schema import MetricTag
from app.dynamics import build_system_dynamics
from app.dynamics.params import DEFAULT_SD_PARAMS
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _charge_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="sd_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _pedestrianisation() -> PolicyDSL:
    return PolicyDSL(
        id="sd_ped",
        intervention=Intervention(type=InterventionType.pedestrianisation),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def test_endpoint_returns_trajectory() -> None:
    res = client.post("/dynamics", json={"policy": _charge_policy().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["provenance"] == "Simulated"
    assert body["political_response_enabled"] is True
    # Trajectory covers the standard Time Machine checkpoints, T0..10y.
    assert len(body["trajectory"]) == 8
    assert body["trajectory"][0]["t_months"] == 0.0
    assert body["trajectory"][-1]["t_months"] == 120.0
    assert body["loop_description"]  # the SPEC §19 cascade, instantiated


def test_recursive_amendment_fires_under_sustained_negative_support() -> None:
    """The SPEC §19 cascade: crowding drives support down → an amendment cuts the charge."""
    r = build_system_dynamics(_charge_policy(), political_response=True)
    assert r.amendments_triggered >= 1
    amendments = [e for e in r.feedback_events if e.type == "amendment"]
    assert amendments
    first = amendments[0]
    # The charge is genuinely lowered, and the causal chain names the cascade.
    assert first.after["charge"] < first.before["charge"]
    assert any("revenue" in step for step in first.cause_chain)


def test_political_response_toggle_changes_outcome() -> None:
    """Closed-loop (response ON) diverges from open-loop (OFF) — the §19 thesis."""
    closed = build_system_dynamics(_charge_policy(), political_response=True)
    openl = build_system_dynamics(_charge_policy(), political_response=False)
    assert openl.amendments_triggered == 0
    # With the political arm on, the charge is amended down below its nominal.
    assert closed.final_state.charge < openl.final_state.charge
    # The contrast payload reports the same divergence, from a single model.
    charge_contrast = next(c for c in closed.contrast if c.metric == "charge")
    assert charge_contrast.delta < 0
    assert charge_contrast.open_loop == 12.0


def test_reinvestment_grows_capacity_general_fund_does_not() -> None:
    """Capacity is a revenue-funded stock: no reinvestment ⇒ no expansion."""
    reinvest = build_system_dynamics(_charge_policy(pt_share=1.0), political_response=False)
    general = build_system_dynamics(_charge_policy(pt_share=0.0), political_response=False)
    base_cap = reinvest.anchors["baseline_capacity"]
    # Full reinvestment expands peak capacity over the horizon...
    assert reinvest.final_state.transit_capacity > base_cap
    # ...while a general-fund split never builds any (capacity stays at baseline).
    assert abs(general.final_state.transit_capacity - base_cap) < 1e-6


def test_no_charge_policy_has_inert_political_arm() -> None:
    """Pedestrianisation has no charge to amend, but the crowding loop still runs."""
    r = build_system_dynamics(_pedestrianisation(), political_response=True)
    assert r.political_response_enabled is False
    assert r.amendments_triggered == 0
    # Displaced trips still load transit → crowding is tracked.
    assert r.final_state.crowding > 0


def test_confidence_widens_with_horizon() -> None:
    r = build_system_dynamics(_charge_policy())
    confs = [pt.confidence for pt in r.trajectory]
    assert confs[0] >= confs[-1]
    assert min(confs) >= DEFAULT_SD_PARAMS.confidence_floor


def test_deterministic() -> None:
    a = build_system_dynamics(_charge_policy())
    b = build_system_dynamics(_charge_policy())
    assert a.model_dump() == b.model_dump()


def test_provenance_is_simulated_and_lists_gaps() -> None:
    r = build_system_dynamics(_charge_policy())
    assert r.provenance == MetricTag.simulated
    assert r.not_modelled  # honest about what the layer omits
    assert "ABM anchors Simulated" in r.anchors["provenance"]
