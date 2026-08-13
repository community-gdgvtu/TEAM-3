"""Tests for the scenario orchestrator ``POST /run`` (SPEC §28/§29).

The orchestrator's whole value is *consistency*: one call must return the same
numbers the standalone endpoints do, all resting on one compiled policy and one
simulation. These tests pin that contract, the auto-amendment logic, and the
§34 guardrails on the composed payload.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


def _compile(text: str = DEMO_TEXT) -> dict:
    r = client.post("/policy/compile", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()["policy"]


def test_run_from_text_composes_full_pipeline() -> None:
    r = client.post("/run", json={"text": DEMO_TEXT})
    assert r.status_code == 200, r.text
    d = r.json()
    for section in ("simulation", "public", "parliament", "amendment", "media"):
        assert section in d and d[section], f"missing section {section}"
    assert d["compiled"] is not None  # text path compiles
    assert len(d["narrative"]) == 6  # the §29 beats
    assert d["headline"], "headline dashboard should not be empty"
    assert d["horizon_label"] == "2 years"  # default horizon


def test_run_accepts_precompiled_policy() -> None:
    policy = _compile()
    r = client.post("/run", json={"policy": policy})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["compiled"] is None  # no compile step when policy supplied
    assert d["policy_id"] == policy["id"]


def test_run_headline_matches_standalone_simulate() -> None:
    """The composed dashboard must equal /simulate's delta at the same horizon."""
    policy = _compile()
    run = client.post("/run", json={"policy": policy, "horizon_months": 24}).json()
    sim = client.post("/simulate", json={"policy": policy}).json()

    delta_by_key = {s["key"]: s for s in sim["delta"]["series"]}
    for tile in run["headline"]:
        series = delta_by_key[tile["key"]]
        point = next(p for p in series["points"] if abs(p["t_months"] - 24) < 1e-9)
        assert abs(tile["world_a"] - point["world_a"]) < 1e-9
        assert abs(tile["world_b"] - point["world_b"]) < 1e-9
        assert abs(tile["delta"] - point["delta"]) < 1e-9


def test_run_net_support_matches_public() -> None:
    policy = _compile()
    run = client.post("/run", json={"policy": policy}).json()
    pub = client.post("/public", json={"policy": policy}).json()
    assert abs(run["net_support"] - pub["overall"]["net_support"]) < 1e-9


def test_run_auto_proposes_low_income_exemption() -> None:
    """A flat charge with no income exemption → equity amendment (SPEC §29 beat)."""
    policy = _compile()
    assert not any("income" in e.lower() for e in policy["exemptions"])
    d = client.post("/run", json={"policy": policy}).json()
    amd = d["amendment"]
    assert amd["proposed"] is True
    assert amd["source"] == "auto:equity"
    assert amd["amendment"]["exempt_low_income"] is True
    assert amd["comparison"] is not None
    # The amendment's own effect series exist (Δ amended − original).
    assert amd["comparison"]["amendment_delta"]["series"]


def test_run_caller_amendment_overrides_auto() -> None:
    policy = _compile()
    body = {
        "policy": policy,
        "amendment": {"label": "halve the charge", "charge_multiplier": 0.5},
    }
    d = client.post("/run", json=body).json()
    assert d["amendment"]["source"] == "caller"
    assert d["amendment"]["amendment"]["charge_multiplier"] == 0.5


def test_run_no_amendment_when_already_equitable() -> None:
    """A charge that already exempts low income + reinvests fully → no amendment."""
    policy = _compile()
    policy["exemptions"] = list(policy["exemptions"]) + ["low-income"]
    policy["revenue_allocation"] = {
        "public_transport": 1.0,
        "general_fund": 0.0,
        "active_travel": 0.0,
        "other": 0.0,
    }
    d = client.post("/run", json={"policy": policy}).json()
    assert d["amendment"]["proposed"] is False
    assert d["amendment"]["source"] == "none"
    assert d["amendment"]["comparison"] is None


def test_run_requires_policy_or_text() -> None:
    r = client.post("/run", json={})
    assert r.status_code == 422  # validator rejects empty input


def test_run_numeric_sections_are_deterministic() -> None:
    """Two identical runs must give byte-identical numbers (prose excluded)."""
    policy = _compile()
    a = client.post("/run", json={"policy": policy}).json()
    b = client.post("/run", json={"policy": policy}).json()
    assert a["simulation"] == b["simulation"]
    assert a["headline"] == b["headline"]
    assert a["net_support"] == b["net_support"]
    assert a["amendment"]["comparison"] == b["amendment"]["comparison"]


def test_run_provenance_and_simulated_media_banner() -> None:
    d = client.post("/run", json={"text": DEMO_TEXT}).json()
    assert any(tag in d["provenance"] for tag in ("Simulated", "Generated"))
    assert "SIMULATED" in str(d["media"]), "media must carry the SIMULATED banner (§15/§34)"
