"""Tests for the policy optimiser stub (ROADMAP stretch, SPEC §22)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.optimiser import optimise_policy

app = create_app()
client = TestClient(app)


def test_returns_candidates_and_pareto_subset() -> None:
    res = optimise_policy({}, {})
    assert res.n_candidates == len(res.candidates) > 0
    front_ids = {c.policy_id for c in res.pareto_front}
    all_ids = {c.policy_id for c in res.candidates}
    assert front_ids <= all_ids
    # Pareto flag on candidates matches the front.
    assert {c.policy_id for c in res.candidates if c.pareto} == front_ids


def test_recommendations_resolve_and_are_extremal() -> None:
    res = optimise_policy({}, {})
    by_id = {c.policy_id: c for c in res.pareto_front}
    r = res.recommendations
    assert r.cheapest in by_id and r.largest_emissions_reduction in by_id
    assert r.most_equitable in by_id and r.best_balanced in by_id
    # Cheapest is the minimum-cost frontier member; emissions pick is the max.
    assert by_id[r.cheapest].metrics.est_cost == min(c.metrics.est_cost for c in res.pareto_front)
    assert by_id[r.largest_emissions_reduction].metrics.emissions_reduction_pct == max(
        c.metrics.emissions_reduction_pct for c in res.pareto_front
    )


def test_budget_constraint_prunes_expensive_candidates() -> None:
    tight = optimise_policy({}, {"max_budget": 50_000_000})
    for c in tight.candidates:
        if c.metrics.est_cost > 50_000_000:
            assert not c.feasible
            assert any("budget" in v or "cost" in v for v in c.violated_constraints)
    assert tight.n_feasible < tight.n_candidates


def test_emissions_target_filters_feasible_set() -> None:
    lax = optimise_policy({"reduce_transport_emissions_pct": 5}, {})
    strict = optimise_policy({"reduce_transport_emissions_pct": 40}, {})
    assert strict.n_feasible < lax.n_feasible


def test_reinvestment_lowers_low_income_burden() -> None:
    res = optimise_policy({}, {})
    most_eq = next(c for c in res.pareto_front if c.policy_id == res.recommendations.most_equitable)
    # The most-equitable frontier pick reinvests a meaningful share into transit.
    assert most_eq.config.public_transport_share >= 0.5


def test_unsatisfiable_constraints_flagged_but_front_returned() -> None:
    res = optimise_policy(
        {"reduce_transport_emissions_pct": 99}, {"max_budget": 1_000}
    )
    assert res.constraints_satisfiable is False
    assert res.n_feasible == 0
    # A frontier is still offered (over all candidates) so the UI isn't empty.
    assert res.pareto_front


def test_endpoint_contract() -> None:
    body = {
        "objective": {"reduce_transport_emissions_pct": 15},
        "constraints": {"max_average_commute_increase_pct": 12, "max_budget": 120_000_000},
    }
    r = client.post("/optimise", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["provenance"] == "Simulated"
    assert data["objective"]["reduce_transport_emissions_pct"] == 15
    assert data["cost_model"] and data["objective_axes"]
    assert data["pareto_front"]


def test_deterministic() -> None:
    a = optimise_policy({"reduce_transport_emissions_pct": 20}, {"max_budget": 100_000_000}).model_dump()
    b = optimise_policy({"reduce_transport_emissions_pct": 20}, {"max_budget": 100_000_000}).model_dump()
    assert a == b
