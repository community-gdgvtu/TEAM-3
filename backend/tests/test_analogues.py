"""Tests for the Historical Analogue / Causal Layer (SPEC §7.1/§8/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.analogues.cases import CASES, CASES_BY_ID
from app.analogues.model import _did, run_analogues
from app.baseline.schema import MetricTag
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _pricing_policy(amount: float = 12.0, reinvest: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_analogue_test",
        intervention=Intervention(type=InterventionType.road_pricing, amount=amount),
        revenue_allocation=RevenueAllocation(
            public_transport=reinvest, general_fund=1.0 - reinvest
        ),
    )


def _ban_policy() -> PolicyDSL:
    return PolicyDSL(
        id="policy_ban_test",
        intervention=Intervention(type=InterventionType.pedestrianisation),
    )


def _transit_policy() -> PolicyDSL:
    return PolicyDSL(
        id="policy_transit_test",
        intervention=Intervention(type=InterventionType.transit_investment),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


# --- Core estimate --------------------------------------------------------


def test_pricing_estimate_is_realistic_and_ordered() -> None:
    r = run_analogues(_pricing_policy())
    # Real flat cordons fall in a plausible band; the pooled estimate must too.
    assert -40.0 <= r.estimated_effect_pct <= -5.0
    # CI brackets the estimate and stays physically valid.
    assert r.ci_low_pct <= r.estimated_effect_pct <= r.ci_high_pct
    assert -100.0 <= r.ci_low_pct <= 0.0
    assert -100.0 <= r.ci_high_pct <= 0.0
    assert r.analogue_quality in {"strong", "moderate", "weak"}


def test_did_effect_is_treated_minus_control() -> None:
    london = CASES_BY_ID["london_ccz"]
    assert _did(london) == london.treated_change_pct - london.control_change_pct
    r = run_analogues(_pricing_policy())
    london_est = next(c for c in r.cases if c.case_id == "london_ccz")
    assert london_est.did_effect_pct == round(
        london.treated_change_pct - london.control_change_pct, 2
    )


def test_pool_weights_normalise_over_applicable_cases() -> None:
    r = run_analogues(_pricing_policy())
    applicable = [c for c in r.cases if c.applicable]
    assert applicable, "a road-pricing policy must have applicable analogues"
    assert abs(sum(c.pool_weight for c in applicable) - 1.0) < 1e-2
    # Non-applicable cases carry zero pool weight and are shown for context.
    for c in r.cases:
        if not c.applicable:
            assert c.pool_weight == 0.0


def test_transferability_prefers_matching_family() -> None:
    # A pure car ban should only pool the pedestrianisation analogue (Ghent).
    r = run_analogues(_ban_policy())
    applicable = [c.case_id for c in r.cases if c.applicable]
    assert applicable == ["ghent_circulation"]


def test_no_analogue_for_transit_only_policy() -> None:
    r = run_analogues(_transit_policy())
    assert all(not c.applicable for c in r.cases)
    assert r.estimated_effect_pct == 0.0
    assert r.transferability_score == 0.0
    assert r.identification_diagnostics
    assert "No comparable" in r.identification_diagnostics[0]


# --- Structural cross-check (SPEC §8 honesty) -----------------------------


def test_structural_comparison_flags_large_gap() -> None:
    r = run_analogues(_pricing_policy())
    sc = r.structural_comparison
    assert sc is not None
    # The agent-based model's cordon collapse is far larger than any real scheme,
    # so the layer must honestly flag the disagreement.
    assert sc.structural_effect_pct < sc.analogue_effect_pct  # more negative
    assert sc.agreement == "large gap"
    assert sc.tag == MetricTag.estimated


def test_structural_comparison_can_be_disabled() -> None:
    r = run_analogues(_pricing_policy(), include_structural_comparison=False)
    assert r.structural_comparison is None


# --- Provenance guardrails (SPEC §34) -------------------------------------


def test_provenance_tags() -> None:
    r = run_analogues(_pricing_policy())
    # The transferred estimate is Estimated; each historical outcome is Observed.
    assert r.provenance == MetricTag.estimated
    for c in r.cases:
        assert c.tag == MetricTag.observed
    for case in CASES:
        assert case.tag == MetricTag.observed
        # Every historical figure is honestly flagged as illustrative.
        assert "illustrative" in case.source_note.lower()


def test_deterministic() -> None:
    a = run_analogues(_pricing_policy()).model_dump()
    b = run_analogues(_pricing_policy()).model_dump()
    assert a == b


# --- HTTP surface ---------------------------------------------------------


def test_endpoint_returns_estimate() -> None:
    res = client.post(
        "/analogues",
        json={
            "policy": {
                "id": "http_test",
                "intervention": {"type": "road_pricing", "amount": 12.0},
                "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
            }
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["provenance"] == "Estimated"
    assert body["estimated_effect_pct"] < 0.0
    assert len(body["cases"]) == len(CASES)
    assert body["structural_comparison"] is not None


def test_cases_endpoint_lists_database() -> None:
    res = client.get("/analogues/cases")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == len(CASES)
    ids = {c["id"] for c in body}
    assert {"london_ccz", "stockholm_tax", "ghent_circulation"} <= ids


def test_registered_in_model_registry() -> None:
    res = client.get("/registry")
    assert res.status_code == 200
    models = {m["id"]: m for m in res.json()["models"]}
    assert "historical_analogue" in models
    # SPEC §34: a numeric layer must never let an LLM touch numbers.
    assert models["historical_analogue"]["llm_touches_numbers"] is False
    assert models["historical_analogue"]["produces_numbers"] is True
