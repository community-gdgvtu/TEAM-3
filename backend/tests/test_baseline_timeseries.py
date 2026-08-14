"""Baseline time-series + ``GET /baseline`` checks — ROADMAP M2, SPEC §9/§34.

Assertions are structural/invariant so they survive re-tuning of the trend
assumptions, plus the guardrails: every projected number is tagged Simulated and
the confidence band widens monotonically into the future.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline import build_timeseries, cached_baseline
from app.baseline.schema import MetricTag
from app.baseline.timeseries import BaselineTrend, _SHARE_KEYS
from app.main import create_app


def test_timeseries_covers_all_snapshot_metrics() -> None:
    snap = cached_baseline()
    ts = build_timeseries(snap)
    assert {s.key for s in ts.series} == {m.key for m in snap.metrics}
    # Every series has exactly one point per checkpoint.
    assert ts.checkpoints[0].label == "T0" and ts.checkpoints[0].t_months == 0.0
    for s in ts.series:
        assert len(s.points) == len(ts.checkpoints)


def test_t0_matches_snapshot_and_all_simulated() -> None:
    snap = cached_baseline()
    by_key = {m.key: m for m in snap.metrics}
    ts = build_timeseries(snap)
    for s in ts.series:
        assert s.tag == MetricTag.simulated
        # T0 central value equals the snapshot value.
        assert s.points[0].value == round(by_key[s.key].value, 3)


def test_uncertainty_band_widens_monotonically() -> None:
    ts = build_timeseries()
    for s in ts.series:
        widths = [p.high - p.low for p in s.points]
        # Band never narrows as the horizon grows (SPEC §9).
        assert all(b >= a - 1e-9 for a, b in zip(widths, widths[1:]))
        # And it is strictly wider at 10y than at T0.
        assert widths[-1] > widths[0]


def test_shares_stay_flat_volumes_grow() -> None:
    ts = build_timeseries()
    for s in ts.series:
        first, last = s.points[0].value, s.points[-1].value
        if s.key in _SHARE_KEYS:
            assert last == first  # no behaviour change without a policy
        elif first > 0:
            assert last > first  # exogenous background demand growth


def test_zero_growth_trend_keeps_central_values_flat() -> None:
    trend = BaselineTrend(demand_growth_per_year=0.0)
    ts = build_timeseries(trend=trend)
    for s in ts.series:
        assert s.points[-1].value == s.points[0].value


def test_get_baseline_endpoint() -> None:
    client = TestClient(create_app())
    resp = client.get("/baseline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["world"] == "A"
    assert body["provenance"] == "Simulated"
    assert body["snapshot"]["mode_share"]["car"] >= 0
    series = body["timeseries"]["series"]
    assert series and all(s["tag"] == "Simulated" for s in series)
    # Trend assumptions are exposed for the Evidence Drawer.
    assert "demand_growth_per_year" in body["timeseries"]["trend"]
