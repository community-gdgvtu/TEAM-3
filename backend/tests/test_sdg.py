"""Tests for the SDG alignment layer (SPEC §23)."""

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
from app.sdg.model import build_sdg_report

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_sdg_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_endpoint_returns_sdg_report() -> None:
    res = client.post("/sdg", json={"policy": _policy().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_sdg_test"
    assert body["provenance"] == "Simulated"
    # Goals present, core/secondary tiers correct (SPEC §23).
    goals = {g["goal"]: g for g in body["goals"]}
    assert set(goals) == {10, 11, 13, 16}
    assert goals[11]["tier"] == "core"
    assert goals[16]["tier"] == "core"
    assert goals[10]["tier"] == "secondary"
    assert goals[13]["tier"] == "secondary"


def test_every_indicator_has_spec23_fields() -> None:
    report = build_sdg_report(_policy())
    seen = 0
    for g in report.goals:
        for ind in g.indicators:
            seen += 1
            # SPEC §23 mandated shape: indicator/proxy, baseline, scenario,
            # change, data source, confidence.
            assert ind.indicator
            assert ind.proxy_for
            assert ind.data_source
            assert 0.0 <= ind.confidence <= 1.0
            assert ind.confidence_label in {"high", "medium", "low"}
            assert ind.better_when in {"higher", "lower"}
            # change is consistent with baseline/scenario.
            assert abs((ind.scenario - ind.baseline) - ind.change) < 1e-6
    assert seen >= 6


def test_no_arbitrary_composite_score() -> None:
    """SPEC §23: do not create an arbitrary 'SDG score'."""
    report = build_sdg_report(_policy())
    # The report exposes only *counts*, never a composite 0-100 score field.
    assert not hasattr(report, "score")
    assert "No composite SDG score" in report.headline
    total = report.total_improved + report.total_worsened + report.total_unchanged
    assert total == sum(len(g.indicators) for g in report.goals)


def test_guardrail_no_llm_generated_numbers() -> None:
    """Every SDG number is Simulated or Estimated — never Generated (SPEC §34)."""
    report = build_sdg_report(_policy())
    for g in report.goals:
        for ind in g.indicators:
            assert ind.tag in {MetricTag.simulated, MetricTag.estimated}
    # Forecast transport indicators come straight from the deterministic sim.
    co2 = _find(report, "sdg13.transport_co2")
    assert co2.tag is MetricTag.simulated


def test_deterministic() -> None:
    a = build_sdg_report(_policy())
    b = build_sdg_report(_policy())
    assert a.model_dump() == b.model_dump()


def test_direction_logic_reduction_is_improvement() -> None:
    """A reinvested cordon cuts CO₂ and CBD traffic → those indicators improve."""
    report = build_sdg_report(_policy(pt_share=1.0))
    co2 = _find(report, "sdg13.transport_co2")
    assert co2.change < 0  # emissions fall
    assert co2.better_when == "lower"
    assert co2.improved is True

    trips = _find(report, "sdg11.cbd_vehicle_trips")
    assert trips.change < 0
    assert trips.improved is True

    sust = _find(report, "sdg11.sustainable_mode_share")
    assert sust.change > 0  # shift toward transit + walking
    assert sust.improved is True


def test_confidence_falls_with_horizon() -> None:
    near = build_sdg_report(_policy(), horizon_months=1.0)
    far = build_sdg_report(_policy(), horizon_months=120.0)
    assert far.horizon.t_months > near.horizon.t_months
    near_co2 = _find(near, "sdg13.transport_co2")
    far_co2 = _find(far, "sdg13.transport_co2")
    # Confidence widens (falls) with the horizon (SPEC §9/§24).
    assert far_co2.confidence < near_co2.confidence


def test_sdg16_process_proxies_are_measured() -> None:
    """SDG 16 proxies are read from the run's own audit artifacts, not invented."""
    report = build_sdg_report(_policy())
    completeness = _find(report, "sdg16.evidence_provenance_completeness")
    # This engine tags every headline metric with provenance + method + assumptions.
    assert completeness.scenario == 100.0
    records = _find(report, "sdg16.structured_reasoning_records")
    # A cordon policy produces a non-empty event ledger.
    assert records.scenario >= 1.0


def _find(report, indicator_id: str):
    for g in report.goals:
        for ind in g.indicators:
            if ind.id == indicator_id:
                return ind
    raise AssertionError(f"indicator {indicator_id} not found")
