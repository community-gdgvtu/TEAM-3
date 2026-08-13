"""Tests for the spatial traffic-assignment layer (SPEC §7.7)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.schema import MetricTag
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.spatial.model import build_spatial_report
from app.spatial.network import Network

app = create_app()
client = TestClient(app)


def _charge_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="spatial_charge",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _pedestrianisation() -> PolicyDSL:
    return PolicyDSL(
        id="spatial_ped",
        intervention=Intervention(type=InterventionType.pedestrianisation, currency="local"),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def _noop_policy() -> PolicyDSL:
    # A transit-investment policy with no charge and no ban → no mode-choice
    # levers change, so World B must equal World A on the road network.
    return PolicyDSL(
        id="spatial_noop",
        intervention=Intervention(type=InterventionType.transit_investment, currency="local"),
    )


# --- Network graph --------------------------------------------------------


def test_network_is_directed_and_connected() -> None:
    net = Network.from_dataset()
    # Every undirected road link becomes two directed arcs.
    assert len(net.arcs) == 144 * 2
    assert len(net.nodes) == 81
    # Free-flow time is positive and consistent with length/speed.
    a = net.arcs[0]
    assert a.t0_min > 0
    # Shortest-path tree from the centre reaches every node.
    dist, _pred = net.shortest_paths("Z040", [arc.t0_min for arc in net.arcs])
    assert len(dist) == 81


# --- Endpoint / shape -----------------------------------------------------


def test_endpoint_returns_report() -> None:
    res = client.post("/spatial", json={"policy": _charge_policy().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "spatial_charge"
    assert body["provenance"] == MetricTag.simulated.value
    for side in ("world_a", "world_b"):
        assert body[side]["cordon_inflow_veh_per_hr"] >= 0
        assert body[side]["mean_vc"] >= 0
    assert body["not_modelled"]  # honesty surface present
    assert "representation_factor" in body["params"]
    assert body["params"]["representation_factor"] > 1.0


def test_deterministic() -> None:
    a = build_spatial_report(_charge_policy())
    b = build_spatial_report(_charge_policy())
    assert a.model_dump() == b.model_dump()


# --- Behaviour ------------------------------------------------------------


def test_charge_reduces_cordon_inflow_and_vehicle_hours() -> None:
    r = build_spatial_report(_charge_policy())
    assert r.world_b.cordon_inflow_veh_per_hr < r.world_a.cordon_inflow_veh_per_hr
    assert r.cordon_inflow_delta_pct < 0
    # Fewer cars in the peak → less total network delay.
    assert r.world_b.total_vehicle_hours < r.world_a.total_vehicle_hours
    # Relieving congestion cannot lower the mean congested speed.
    assert r.world_b.mean_speed_kmh >= r.world_a.mean_speed_kmh


def test_pedestrianisation_collapses_cordon_inflow() -> None:
    r = build_spatial_report(_pedestrianisation())
    # A car ban on CBD-bound trips drives cordon inflow far below the charge.
    charge = build_spatial_report(_charge_policy())
    assert r.world_b.cordon_inflow_veh_per_hr <= charge.world_b.cordon_inflow_veh_per_hr
    assert r.cordon_inflow_delta_pct < -50.0


def test_noop_policy_leaves_network_unchanged() -> None:
    r = build_spatial_report(_noop_policy())
    assert r.peak_hour_car_trips_a == r.peak_hour_car_trips_b
    assert r.world_a.cordon_inflow_veh_per_hr == r.world_b.cordon_inflow_veh_per_hr
    assert r.cordon_inflow_delta_pct == 0.0


def test_charge_cuts_central_pollution() -> None:
    r = build_spatial_report(_charge_policy())
    assert r.pollution.cbd_b < r.pollution.cbd_a
    assert r.pollution.cbd_delta_pct < 0
    # Every reported zone change carries a Simulated provenance on the report.
    assert r.pollution.tag == MetricTag.simulated


def test_accessibility_not_worsened_by_charge() -> None:
    r = build_spatial_report(_charge_policy())
    # Cutting congestion should not reduce mean job accessibility.
    assert r.accessibility.mean_b >= r.accessibility.mean_a
    assert r.accessibility.mean_delta_pct >= 0.0


def test_notable_arcs_include_cordon_links() -> None:
    r = build_spatial_report(_charge_policy())
    assert any(a.crosses_cordon for a in r.notable_arcs)
    # Cordon arcs should show reduced flow under the charge.
    cordon = [a for a in r.notable_arcs if a.crosses_cordon]
    assert any(a.flow_b < a.flow_a for a in cordon)
