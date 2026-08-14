"""Event-ledger checks — ROADMAP M3, SPEC §10/§34.

The ledger must be derived deterministically from the model output, carry the
SPEC §10 fields (cause/affected/confidence/downstream), fire the canonical
events for a cordon-charge policy, and stay tagged Simulated.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline import compute_baseline
from app.baseline.schema import MetricTag
from app.baseline.timeseries import build_timeseries
from app.main import app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation import build_delta, build_event_ledger, compute_world_b
from app.simulation.timeline import build_world_b_timeline

client = TestClient(app)


def _pricing_policy(amount: float = 12.0, pt_share: float = 1.0, impl: str | None = None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_ledger_test",
        intervention=Intervention(
            type=InterventionType.road_pricing,
            amount=amount,
            currency="local",
            geographic_zone="cbd_polygon",
            implementation_date=impl,
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _ledger_for(policy: PolicyDSL):
    base = compute_baseline()
    a_ts = build_timeseries(base)
    b_ts = build_world_b_timeline(policy, baseline=base)
    delta = build_delta(a_ts, b_ts)
    return build_event_ledger(policy, base, delta)


def test_ledger_fires_expected_events_for_cordon_charge() -> None:
    ledger = _ledger_for(_pricing_policy())
    types = {e.type for e in ledger.events}
    # A meaningful cordon charge must at least shift modes and drop cordon load.
    assert "mode_shift" in types
    assert "cordon_load" in types
    assert ledger.provenance == MetricTag.simulated


def test_events_have_spec10_fields() -> None:
    ledger = _ledger_for(_pricing_policy())
    assert ledger.events
    for e in ledger.events:
        assert e.type and e.description
        assert e.cause  # non-empty upstream causes
        assert e.downstream  # non-empty downstream effects
        assert 0.0 <= e.confidence <= 1.0
        assert e.affected_agents >= 0
        assert e.provenance == MetricTag.simulated


def test_events_sorted_by_month() -> None:
    ledger = _ledger_for(_pricing_policy())
    months = [e.scenario_month for e in ledger.events]
    assert months == sorted(months)


def test_confidence_decreases_with_horizon() -> None:
    # Two events at different horizons: the later one is no more confident.
    ledger = _ledger_for(_pricing_policy())
    by_month = sorted(ledger.events, key=lambda e: e.scenario_month)
    if len(by_month) >= 2 and by_month[0].scenario_month != by_month[-1].scenario_month:
        assert by_month[-1].confidence <= by_month[0].confidence + 1e-9


def test_timestamp_derived_when_impl_date_present() -> None:
    ledger = _ledger_for(_pricing_policy(impl="2027-01-01"))
    dated = [e for e in ledger.events if e.scenario_month > 0]
    assert dated and all(e.timestamp is not None for e in dated)
    # Absent an implementation date, timestamps stay null.
    ledger2 = _ledger_for(_pricing_policy(impl=None))
    assert all(e.timestamp is None for e in ledger2.events)


def test_no_reinvestment_event_without_allocation() -> None:
    ledger = _ledger_for(_pricing_policy(pt_share=0.0))
    assert all(e.type != "transit_reinvestment" for e in ledger.events)


def test_ledger_exposed_on_simulate_endpoint() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        }
    }
    data = client.post("/simulate", json=body).json()
    assert "event_ledger" in data
    assert data["event_ledger"]["provenance"] == "Simulated"
    assert any(e["type"] == "mode_shift" for e in data["event_ledger"]["events"])
