"""Tests for the global one-at-a-time sensitivity tornado (SPEC §24/§26).

The layer must (1) rank assumptions by cross-metric leverage, (2) stay perfectly
consistent with the deterministic pipeline / the §24 uncertainty engine, (3) be
byte-identical on repeat (deterministic, no sampling), and (4) be honest about a
policy whose outcomes no assumption moves (SPEC §34).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.sensitivity import run_sensitivity
from app.uncertainty import run_uncertainty
from app.uncertainty.engine import ASSUMPTIONS

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_sensitivity_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _body(**extra: object) -> dict:
    return {"policy": _policy().model_dump(mode="json"), **extra}


def test_endpoint_ok_and_estimated() -> None:
    r = client.post("/sensitivity", json=_body(horizon_months=60))
    assert r.status_code == 200
    j = r.json()
    assert j["provenance"] == "Estimated"
    assert j["horizon"]["t_months"] == 60.0
    # Sweeps exactly the documented assumption set the uncertainty engine uses.
    assert j["swept_assumptions"] == [a.name for a in ASSUMPTIONS]
    assert len(j["tornados"]) >= 5
    assert j["not_modelled"]  # honest scope limits present


def test_drivers_ranked_by_descending_leverage() -> None:
    res = run_sensitivity(_policy(), horizon_months=60)
    scores = [d.global_score for d in res.drivers]
    assert scores == sorted(scores, reverse=True)
    # Every driver corresponds to a swept assumption; one card per assumption.
    assert {d.name for d in res.drivers} == {a.name for a in ASSUMPTIONS}
    # The headline names the top *active* driver.
    active = [d for d in res.drivers if d.matters]
    assert active and active[0].label in res.headline


def test_per_metric_influence_shares_sum_to_one() -> None:
    res = run_sensitivity(_policy(), horizon_months=60)
    for t in res.tornados:
        total = sum(b.influence_share for b in t.bars)
        # Shares are a partition of each metric's sensitivity (0 only if fully
        # flat); allow rounding slack from per-bar 4-dp rounding.
        assert abs(total - 1.0) < 2e-3 or total == 0.0
        # Bars are ranked most→least influential.
        assert [b.abs_swing for b in t.bars] == sorted(
            (b.abs_swing for b in t.bars), reverse=True
        )
        # abs_swing matches |delta_high - delta_low| and direction agrees with sign.
        for b in t.bars:
            assert abs(b.abs_swing - abs(b.delta_at_high - b.delta_at_low)) < 1e-3
            sign = b.delta_at_high - b.delta_at_low
            expect = "up" if sign > 1e-9 else ("down" if sign < -1e-9 else "flat")
            assert b.direction == expect
        if t.most_influential is not None:
            assert t.bars[0].name == t.most_influential


def test_consistent_with_uncertainty_engine_sensitivity() -> None:
    """Same pipeline ⇒ the OAT swings here must match /uncertainty's per-metric
    sensitivity ranking (both re-run the deterministic model at the same edges)."""
    metric = "transit.daily_transit_trips"
    unc = run_uncertainty(_policy(), metric, samples=20, horizon_months=60)
    sens = run_sensitivity(_policy(), horizon_months=60)
    tornado = next(t for t in sens.tornados if t.key == metric)
    unc_swing = {e.name: e.swing for e in unc.influential_assumptions}
    sens_swing = {b.name: b.abs_swing for b in tornado.bars}
    for name, sw in unc_swing.items():
        assert abs(sens_swing[name] - sw) < 1e-2, name


def test_deterministic_byte_identical_repeat() -> None:
    a = client.post("/sensitivity", json=_body()).json()
    b = client.post("/sensitivity", json=_body()).json()
    assert a == b


def test_flat_assumptions_flagged_not_mattering() -> None:
    """`matters` must be exactly "moves at least one metric" — an assumption flat
    on every metric is honestly flagged, not silently ranked as if influential
    (SPEC §34). Property-based so it holds for any policy."""
    res = run_sensitivity(_policy(pt_share=0.0), horizon_months=60)
    # A general-fund charge (no reinvestment) leaves the reinvestment knobs inert.
    swing_by_assumption: dict[str, float] = {}
    for t in res.tornados:
        for b in t.bars:
            swing_by_assumption[b.name] = max(swing_by_assumption.get(b.name, 0.0), b.abs_swing)
    for d in res.drivers:
        moves_something = swing_by_assumption.get(d.name, 0.0) > 1e-9
        assert d.matters is moves_something
        if not d.matters:
            assert d.global_score == 0.0
            assert d.top_metric is None
            assert "does not rest on it" in d.note
    # This policy has at least one genuinely inert assumption to exercise the flag.
    assert any(not d.matters for d in res.drivers)


def test_no_effect_policy_reports_structural_headline() -> None:
    """A behavioural nudge with no priced lever should move no metric, and the
    layer should say so rather than invent a driver."""
    nudge = PolicyDSL(
        id="policy_nudge",
        intervention=Intervention(type=InterventionType.other, amount=0.0),
    )
    res = run_sensitivity(nudge, horizon_months=60)
    assert all(not d.matters for d in res.drivers)
    assert "structural" in res.headline.lower() or "does not" in res.headline.lower()


def test_metric_subset_and_fallback() -> None:
    only = run_sensitivity(_policy(), metric_keys=["traffic.daily_vehicle_km"])
    assert [t.key for t in only.tornados] == ["traffic.daily_vehicle_km"]
    # An unknown key set falls back to the full dashboard rather than 500-ing.
    full = run_sensitivity(_policy(), metric_keys=["does.not.exist"])
    assert len(full.tornados) >= 5


def test_registered_in_model_registry() -> None:
    reg = client.get("/registry").json()
    card = next(m for m in reg["models"] if m["id"] == "sensitivity_tornado")
    assert card["llm_touches_numbers"] is False
    assert card["output_tag"] == "Estimated"
    assert "§26" in card["spec_sections"]
