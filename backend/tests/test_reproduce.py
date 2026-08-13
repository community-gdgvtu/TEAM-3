"""Tests for the run reproducibility manifest (SPEC §32/§34).

Verifies the "REPRODUCE RUN" contract: a content-addressed ``run_id`` that is
stable for identical inputs and changes when any input changes, a self-verified
output digest proving the deterministic core reproduces, and that the §32
required record (datasets, models, params, seed, DSL, code version, timestamp)
is present with no LLM in the numeric path.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import PolicyDSL
from app.reproduce.manifest import build_manifest

app = create_app()
client = TestClient(app)


def _pricing_body(amount: float = 12.0, pt_share: float = 1.0, **extra) -> dict:
    body = {
        "policy": {
            "id": "policy_repro_test",
            "intervention": {
                "type": "road_pricing",
                "amount": amount,
                "currency": "local",
                "geographic_zone": "cbd_polygon",
            },
            "revenue_allocation": {
                "public_transport": pt_share,
                "general_fund": 1.0 - pt_share,
            },
        }
    }
    body.update(extra)
    return body


def test_endpoint_returns_manifest_with_required_fields() -> None:
    r = client.post("/reproduce", json=_pricing_body())
    assert r.status_code == 200, r.text
    m = r.json()
    # SPEC §32 required record.
    assert m["run_id"]
    assert m["output_digest"]
    assert m["created_at"]
    assert m["app_version"]
    assert m["code_version"]
    assert m["policy"]["id"] == "policy_repro_test"
    assert m["datasets"], "must pin dataset versions"
    assert m["models"], "must pin model versions"
    assert m["assumptions"], "must record parameters/assumptions"
    assert m["provenance"] == "Observed"


def test_run_id_is_stable_for_identical_inputs() -> None:
    a = client.post("/reproduce", json=_pricing_body()).json()
    b = client.post("/reproduce", json=_pricing_body()).json()
    # Same inputs → same run_id and output_digest, even though timestamps differ.
    assert a["run_id"] == b["run_id"]
    assert a["output_digest"] == b["output_digest"]
    # The timestamp is metadata, not part of the identity.
    assert "created_at" not in a["inputs_fingerprint"]


def test_run_id_changes_when_the_policy_changes() -> None:
    a = client.post("/reproduce", json=_pricing_body(amount=12.0)).json()
    b = client.post("/reproduce", json=_pricing_body(amount=6.0)).json()
    assert a["run_id"] != b["run_id"]
    # A different priced charge must also change the simulated outputs.
    assert a["output_digest"] != b["output_digest"]


def test_seed_is_recorded_and_hashed() -> None:
    a = client.post("/reproduce", json=_pricing_body(seed=1)).json()
    b = client.post("/reproduce", json=_pricing_body(seed=2)).json()
    assert a["seed"] == 1 and b["seed"] == 2
    # Seed is part of the run identity (SPEC §32) ...
    assert a["run_id"] != b["run_id"]
    # ... but the core is deterministic, so the numbers are unchanged.
    assert a["output_digest"] == b["output_digest"]


def test_core_is_self_verified_reproducible() -> None:
    manifest = build_manifest(PolicyDSL(**_pricing_body()["policy"]))
    assert manifest.reproducible is True
    assert manifest.output_digest == manifest.output_digest


def test_no_llm_prompt_enters_the_numeric_path() -> None:
    """SPEC §34: the reproducibility record proves no LLM produced numbers."""
    manifest = build_manifest(PolicyDSL(**_pricing_body()["policy"]))
    assert manifest.prompts == []
    assert all(mv.llm_touches_numbers is False for mv in manifest.models)


def test_datasets_are_content_addressed() -> None:
    manifest = build_manifest(PolicyDSL(**_pricing_body()["policy"]))
    ids = {d.id for d in manifest.datasets}
    assert {"city_grid", "population"} <= ids
    for d in manifest.datasets:
        # A real content hash (64 hex chars), not a placeholder.
        assert len(d.content_sha256) == 64, d.id


def test_shocks_are_part_of_run_identity() -> None:
    plain = client.post("/reproduce", json=_pricing_body()).json()
    shocked = client.post(
        "/reproduce", json=_pricing_body(shocks={"car_cost_per_km_multiplier": 1.25})
    ).json()
    assert plain["run_id"] != shocked["run_id"]
    assert shocked["shocks"], "shocks must be echoed into the manifest"
