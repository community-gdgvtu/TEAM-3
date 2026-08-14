"""Tests for the opinion-diffusion engine (SPEC §14)."""

from __future__ import annotations

from collections import defaultdict

from fastapi.testclient import TestClient

from app.diffusion.model import run_diffusion
from app.diffusion.schema import InfoShock
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _policy(pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_diffusion_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=12.0, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_endpoint_shape() -> None:
    res = client.post("/diffusion", json={"policy": _policy().model_dump(), "rounds": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["provenance"] == "Simulated"
    assert body["rounds"] == 10
    assert body["nodes"] and body["edges"]
    # Every trajectory has one opinion per round (round 0 … round N).
    for tr in body["trajectories"]:
        assert len(tr["opinions"]) == 11
    assert len(body["salience"]) == 11
    assert len(body["polarisation"]) == 11


def test_graph_has_all_spec14_actor_types() -> None:
    r = run_diffusion(_policy())
    types = {n.type for n in r.nodes}
    # SPEC §14 node taxonomy.
    for required in (
        "cohort",
        "journalist",
        "politician",
        "institution",
        "influencer",
        "community_group",
    ):
        assert required in types


def test_influence_matrix_is_row_stochastic() -> None:
    """Each node's incoming influence weights sum to 1 (Friedkin–Johnsen)."""
    r = run_diffusion(_policy())
    incoming = defaultdict(float)
    for e in r.edges:
        incoming[e.target] += e.weight
    for node in r.nodes:
        # Edge weights are rounded to 4dp for display; allow that tolerance.
        assert abs(incoming[node.id] - 1.0) < 1e-3


def test_opinions_bounded() -> None:
    r = run_diffusion(_policy(), rounds=20)
    for tr in r.trajectories:
        for o in tr.opinions:
            assert -1.0 <= o <= 1.0


def test_citizen_seed_matches_opinion_model() -> None:
    """Citizen round-0 opinions come from the deterministic cohort model."""
    from app.opinion.model import compute_public_opinion

    op = compute_public_opinion(_policy())
    agg: dict[str, list[float]] = {}
    for c in op.cohorts:
        agg.setdefault(c.income_band, [0.0, 0.0])
        agg[c.income_band][0] += c.mean_support * c.size
        agg[c.income_band][1] += c.size
    r = run_diffusion(_policy())
    low = next(n for n in r.nodes if n.id == "citizen_low")
    expected = agg["low"][0] / agg["low"][1]
    assert abs(low.initial_opinion - expected) < 1e-3


def test_deterministic() -> None:
    a = run_diffusion(_policy(), rounds=12)
    b = run_diffusion(_policy(), rounds=12)
    assert a.model_dump() == b.model_dump()


def test_info_shock_moves_opinion() -> None:
    """A durable narrative shock shifts the final citizen net support (SPEC §14)."""
    base = run_diffusion(_policy(), rounds=12)
    scandal = run_diffusion(
        _policy(),
        rounds=12,
        info_shocks=[InfoShock(round=2, node="journalists", delta=-0.8, label="scandal")],
    )
    assert scandal.final_net_support < base.final_net_support
    pro = run_diffusion(
        _policy(),
        rounds=12,
        info_shocks=[InfoShock(round=1, node="influencers", delta=0.7)],
    )
    assert pro.final_net_support > base.final_net_support


def test_coalitions_partition_all_nodes() -> None:
    r = run_diffusion(_policy())
    members = [m for c in r.coalitions for m in c.members]
    # Every node lands in exactly one coalition.
    assert sorted(members) == sorted(n.id for n in r.nodes)
    assert len(members) == len(set(members))
    for c in r.coalitions:
        assert c.stance in {"support", "oppose", "contested"}


def test_salience_and_polarisation_in_range() -> None:
    r = run_diffusion(_policy(), rounds=15)
    for v in r.salience + r.polarisation:
        assert 0.0 <= v <= 1.0
