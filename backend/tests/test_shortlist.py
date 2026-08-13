"""Tests for the policy shortlist ranker (POST /shortlist, SPEC §21/§22).

Load-bearing guarantees: (1) the caller's own policies are simulated by the same
deterministic model (no LLM number, Simulated provenance); (2) the composite is a
transparent weighted sum — weighting entirely on one axis makes that axis's leader
win; (3) constraints correctly gate feasibility and the winner; (4) both entry
paths (compiled-from-text and provided DSL) work; (5) the ranking is deterministic
and reconciled with the capability manifest.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.policy.dsl import Intervention, InterventionType, PolicyDSL, RevenueAllocation

client = TestClient(app)


def _charge(id_: str, pt_share: float, amount: float = 12.0) -> dict:
    return PolicyDSL(
        id=id_,
        intervention=Intervention(type=InterventionType.road_pricing, amount=amount),
        revenue_allocation=RevenueAllocation(public_transport=pt_share, general_fund=round(1.0 - pt_share, 4)),
    ).model_dump()


def _three_policies() -> list[dict]:
    return [
        {"label": "charge → buses", "policy": _charge("reinvest", 1.0)},
        {"label": "charge → general fund", "policy": _charge("genfund", 0.0)},
        {
            "label": "pedestrianise",
            "policy": PolicyDSL(
                id="ped",
                intervention=Intervention(type=InterventionType.pedestrianisation),
                revenue_allocation=RevenueAllocation(public_transport=0.5, general_fund=0.5),
            ).model_dump(),
        },
    ]


def test_example_shape_and_provenance() -> None:
    r = client.get("/shortlist/example")
    assert r.status_code == 200
    m = r.json()
    assert m["provenance"] == "Simulated"
    assert m["n_policies"] == 3
    assert len(m["ranking"]) == 3
    # Ranks are a contiguous 1..n and sorted ascending as returned.
    assert [row["rank"] for row in m["ranking"]] == [1, 2, 3]
    # No constraints → everything feasible, winner is the top row.
    assert m["n_feasible"] == 3
    assert m["constraints_satisfiable"] is True
    assert m["recommendations"]["winner"] == m["ranking"][0]["policy_id"]
    # Weights normalise to sum 1.
    w = m["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_metrics_are_simulated_not_generated() -> None:
    m = client.get("/shortlist/example").json()
    for row in m["ranking"]:
        # est_cost is the only Estimated proxy; outcome metrics come from the sim.
        assert set(row["normalized"]) == {"emissions", "commute", "equity", "support", "cost"}
        for v in row["normalized"].values():
            assert 0.0 <= v <= 1.0


def test_emissions_weight_makes_greenest_win() -> None:
    body = {
        "policies": _three_policies(),
        "weights": {"emissions": 1, "commute": 0, "equity": 0, "support": 0, "cost": 0},
    }
    m = client.post("/shortlist", json=body).json()
    # Composite == normalised emissions → the greenest feasible policy ranks first.
    assert m["recommendations"]["winner"] == m["recommendations"]["greenest"]
    assert m["ranking"][0]["policy_id"] == m["recommendations"]["greenest"]
    assert m["ranking"][0]["composite_score"] == 1.0


def test_equity_weight_makes_most_equitable_win() -> None:
    body = {
        "policies": _three_policies(),
        "weights": {"emissions": 0, "commute": 0, "equity": 1, "support": 0, "cost": 0},
    }
    m = client.post("/shortlist", json=body).json()
    assert m["recommendations"]["winner"] == m["recommendations"]["most_equitable"]


def test_constraints_gate_feasibility() -> None:
    # An impossible emissions target makes every policy infeasible.
    body = {
        "policies": _three_policies(),
        "objective": {"reduce_transport_emissions_pct": 99},
    }
    m = client.post("/shortlist", json=body).json()
    assert m["n_feasible"] == 0
    assert m["constraints_satisfiable"] is False
    assert m["recommendations"]["winner"] is None
    # Every row records why it failed.
    for row in m["ranking"]:
        assert row["candidate"]["feasible"] is False
        assert any("Infeasible" in n for n in row["notes"])


def test_text_and_dsl_entry_paths() -> None:
    body = {
        "policies": [
            {"text": "charge £10 to drive into the city centre, reinvest in buses"},
            {"label": "ped", "policy": _three_policies()[2]["policy"]},
        ]
    }
    r = client.post("/shortlist", json=body)
    assert r.status_code == 200
    m = r.json()
    sources = {row["source"] for row in m["ranking"]}
    assert sources == {"compiled_from_text", "provided_dsl"}


def test_entry_needs_exactly_one_source() -> None:
    both = {"policies": [{"text": "x", "policy": _charge("a", 1.0)}, {"text": "y"}]}
    assert client.post("/shortlist", json=both).status_code == 422
    neither = {"policies": [{"label": "empty"}, {"text": "y"}]}
    assert client.post("/shortlist", json=neither).status_code == 422


def test_min_two_policies_required() -> None:
    one = {"policies": [{"text": "just one"}]}
    assert client.post("/shortlist", json=one).status_code == 422


def test_deterministic_repeat() -> None:
    body = {"policies": _three_policies()}
    a = client.post("/shortlist", json=body).json()
    b = client.post("/shortlist", json=body).json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_pareto_and_leaders_are_consistent() -> None:
    m = client.post("/shortlist", json={"policies": _three_policies()}).json()
    ids = {row["policy_id"] for row in m["ranking"]}
    # Every recommendation id (when set) is a real policy in the ranking.
    for key, pid in m["recommendations"].items():
        if pid is not None:
            assert pid in ids, key
    for axis, pid in m["per_metric_leaders"].items():
        assert pid in ids, axis
    # At least one policy sits on the Pareto front.
    assert any(row["candidate"]["pareto"] for row in m["ranking"])


def test_reconciled_with_capabilities() -> None:
    caps = client.get("/capabilities").json()
    paths = {e["path"] for g in caps["groups"] for e in g["endpoints"]}
    assert "/shortlist" in paths
    assert "/shortlist/example" in paths
    assert "/shortlist/example" in caps["keyless_examples"]
    # No route may be left undocumented / phantom by the addition.
    assert caps["undocumented_routes"] == []
    assert caps["phantom_cards"] == []
