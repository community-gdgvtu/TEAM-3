"""Tests for the decision-under-uncertainty layer (SPEC §20/§21/§22).

Every payoff is a deterministic Δ(B−A) composed from the stress core; these tests
pin that composition (regret matrix, the five decision criteria, determinism) and
the §34 honesty guarantees (no LLM, payoffs identical to the stress endpoint).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.robustness.model import _decide, _headline
from app.robustness.schema import CandidateScore, StateResult

client = TestClient(app)


def _candidate(cid: str, amount: float, pt_share: float, exempt: bool = False) -> dict:
    pol = PolicyDSL(
        id=cid,
        intervention=Intervention(type=InterventionType.road_pricing, amount=amount),
        exemptions=(["low-income"] if exempt else []),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=round(1.0 - pt_share, 4)
        ),
    )
    return pol.model_dump(mode="json")


def _default_candidates() -> list[dict]:
    return [
        _candidate("cand_0", 6.0, 1.0),
        _candidate("cand_1", 18.0, 0.0),
        _candidate("cand_2", 12.0, 0.5, exempt=True),
    ]


def test_report_shape_and_provenance():
    body = {"candidates": _default_candidates()}
    r = client.post("/robustness", json=body)
    assert r.status_code == 200
    d = r.json()
    assert d["provenance"] == "Simulated"  # §34: no LLM, deterministic delta
    assert d["objective_key"] == "emissions.daily_co2_tonnes"  # default
    # Baseline is always the first state, then the full §20 shock set.
    assert d["states"][0] == "baseline"
    assert len(d["states"]) == 9  # baseline + 8 shocks
    assert len(d["candidates"]) == 3
    for cs in d["candidates"]:
        assert len(cs["states"]) == len(d["states"])
        assert cs["states"][0]["state_key"] == "baseline"


def test_regret_matrix_is_nonnegative_and_zero_for_best():
    r = client.post("/robustness", json={"candidates": _default_candidates()})
    d = r.json()
    n_states = len(d["states"])
    for s in range(n_states):
        regrets = [cs["states"][s]["regret"] for cs in d["candidates"]]
        assert all(x >= -1e-9 for x in regrets)  # regret is never negative
        assert min(regrets) <= 1e-9  # the per-state best candidate has zero regret


def test_decision_criteria_agree_with_scores():
    r = client.post("/robustness", json={"candidates": _default_candidates()})
    d = r.json()
    cands = {c["policy_id"]: c for c in d["candidates"]}
    picks = d["picks"]
    # Each pick is the argmax/argmin of the corresponding score.
    assert cands[picks["nominal_best"]]["nominal_payoff"] == max(
        c["nominal_payoff"] for c in d["candidates"]
    )
    assert cands[picks["maximin"]]["worst_case_payoff"] == max(
        c["worst_case_payoff"] for c in d["candidates"]
    )
    assert cands[picks["minimax_regret"]]["max_regret"] == min(
        c["max_regret"] for c in d["candidates"]
    )
    assert cands[picks["laplace"]]["mean_payoff"] == max(
        c["mean_payoff"] for c in d["candidates"]
    )
    assert cands[picks["most_robust"]]["robustness_score"] == max(
        c["robustness_score"] for c in d["candidates"]
    )


def test_deterministic_byte_identical():
    body = {"candidates": _default_candidates(), "horizon_months": 60}
    a = client.post("/robustness", json=body).json()
    b = client.post("/robustness", json=body).json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_payoff_matches_stress_core_exactly():
    """§34 honesty: a robustness payoff is the SAME number the stress core returns."""
    cands = _default_candidates()
    horizon = 60
    rob = client.post(
        "/robustness",
        json={"candidates": cands, "horizon_months": horizon},
    ).json()
    st = client.post(
        "/stress-test",
        json={"policy": cands[0], "scenarios": ["recession"], "horizon_months": horizon},
    ).json()
    em = next(m for m in st["baseline"]["metrics"] if m["key"] == "emissions.daily_co2_tonnes")
    # emissions is a 'decrease' good, so benefit = -delta.
    expected = -em["delta_baseline"]
    base_payoff = next(
        s for s in rob["candidates"][0]["states"] if s["state_key"] == "baseline"
    )["payoff"]
    assert base_payoff == pytest.approx(expected, abs=1e-6)


def test_scenario_subset_and_objective_override():
    body = {
        "candidates": _default_candidates(),
        "scenarios": ["recession", "fuel_price_spike"],
        "objective": "transit.daily_transit_trips",
    }
    d = client.post("/robustness", json=body).json()
    assert d["states"] == ["baseline", "recession", "fuel_price_spike"]
    assert d["objective_key"] == "transit.daily_transit_trips"
    assert d["objective_direction"] == "increase"


def test_confidence_widens_with_horizon():
    """A 'modelled' baseline state is 'high' short-run but widens by 5y (SPEC §24)."""
    short = client.post(
        "/robustness", json={"candidates": _default_candidates(), "horizon_months": 1}
    ).json()
    long = client.post(
        "/robustness", json={"candidates": _default_candidates(), "horizon_months": 120}
    ).json()

    def base_conf(rep):
        return rep["candidates"][0]["states"][0]["confidence"]

    order = {"high": 3, "medium": 2, "low": 1}
    assert order[base_conf(long)] <= order[base_conf(short)]


def test_error_paths():
    cands = _default_candidates()
    assert client.post("/robustness", json={"candidates": cands[:1]}).status_code == 422
    assert (
        client.post("/robustness", json={"candidates": cands, "objective": "nope"}).status_code
        == 404
    )
    assert (
        client.post(
            "/robustness", json={"candidates": cands, "scenarios": ["nope"]}
        ).status_code
        == 404
    )


def test_objectives_endpoint():
    d = client.get("/robustness/objectives").json()
    assert d["default"] == "emissions.daily_co2_tonnes"
    assert "transit.daily_transit_trips" in d["objectives"]


# --- unit tests for the decision logic branches (deterministic, no HTTP) --------


def _score(pid, nominal, worst, mean, max_regret, robust) -> CandidateScore:
    # states list is not exercised by _decide/_headline beyond max_regret/nominal.
    return CandidateScore(
        policy_id=pid,
        label=pid,
        states=[
            StateResult(
                state_key="baseline",
                state_label="Baseline (no shock)",
                category="reference",
                payoff=nominal,
                regret=0.0,
                confidence="high",
            )
        ],
        nominal_payoff=nominal,
        worst_case_payoff=worst,
        best_case_payoff=max(nominal, worst),
        mean_payoff=mean,
        max_regret=max_regret,
        robustness_score=robust,
        holds_under=[],
        fails_under=[],
    )


def test_headline_flip_when_robust_differs_from_nominal():
    # A wins the headline but has huge worst-case regret; B is the safe pick.
    a = _score("A", nominal=10.0, worst=-5.0, mean=2.0, max_regret=9.0, robust=0.2)
    b = _score("B", nominal=8.0, worst=6.0, mean=7.0, max_regret=1.0, robust=1.0)
    picks = _decide([a, b])
    assert picks.nominal_best == "A"
    assert picks.minimax_regret == "B"
    assert picks.maximin == "B"
    head = _headline([a, b], picks, "emissions.daily_co2_tonnes")
    assert "NOT the robust choice" in head


def test_headline_no_tradeoff_when_one_dominates():
    a = _score("A", nominal=10.0, worst=9.0, mean=9.5, max_regret=0.0, robust=1.0)
    b = _score("B", nominal=8.0, worst=2.0, mean=5.0, max_regret=3.0, robust=0.5)
    picks = _decide([a, b])
    assert picks.nominal_best == picks.minimax_regret == picks.maximin == "A"
    head = _headline([a, b], picks, "emissions.daily_co2_tonnes")
    assert "no-trade-off" in head
