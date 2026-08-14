"""Tests for the Data Fabric ingestion & provenance layer (SPEC §4/§34)."""

from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from app.datafabric.model import build_data_fabric
from app.dataset import data_dir
from app.main import create_app

app = create_app()
client = TestClient(app)


def test_endpoint_returns_fabric() -> None:
    res = client.get("/data-fabric")
    assert res.status_code == 200
    body = res.json()
    assert body["app_version"]
    # The fabric describes the data on disk → Observed about itself (SPEC §4).
    assert body["provenance"] == "Observed"
    assert body["datasets"]
    assert body["format_support"]
    assert body["harmonisation"]
    assert body["lineage_contract"] == "input data → transformation → model → assumptions → result"


def test_every_dataset_carries_the_full_spec4_schema() -> None:
    """SPEC §4: each dataset must store the mandated provenance record."""
    fabric = build_data_fabric()
    required = {
        "title",
        "publisher",
        "source_url",
        "geographic_scope",
        "units",
        "variables",
        "license",
        "missingness",
        "revision",
        "confidence",
        "transformation_history",
    }
    for ds in fabric.datasets:
        d = ds.model_dump()
        for field in required:
            assert field in d and d[field] is not None, f"{ds.id} missing {field}"
        # Every dataset has at least one described variable and a lineage step.
        assert ds.variables, f"{ds.id} has no variables"
        assert ds.transformation_history, f"{ds.id} has no transformation_history"


def test_revision_is_the_live_content_hash_of_the_file() -> None:
    """revision must be a content address of the actual bytes (not hand-copied)."""
    fabric = build_data_fabric()
    d = data_dir()
    file_map = {
        "zones": "zones.geojson",
        "roads": "roads.geojson",
        "od_pairs": "od_pairs.json",
        "population": "population.json",
    }
    by_id = {ds.id: ds for ds in fabric.datasets}
    for ds_id, fname in file_map.items():
        expected = "sha256:" + hashlib.sha256((d / fname).read_bytes()).hexdigest()[:12]
        assert by_id[ds_id].revision == expected


def test_record_counts_match_the_files() -> None:
    fabric = build_data_fabric()
    d = data_dir()
    by_id = {ds.id: ds for ds in fabric.datasets}

    zones = json.loads((d / "zones.geojson").read_text())
    assert by_id["zones"].record_count == len(zones["features"])

    od = json.loads((d / "od_pairs.json").read_text())
    assert by_id["od_pairs"].record_count == len(od["pairs"])

    pop = json.loads((d / "population.json").read_text())
    assert by_id["population"].record_count == len(pop["agents"])


def test_missingness_is_measured_and_variables_agree() -> None:
    """Overall missingness must equal the mean of the per-variable measurements."""
    fabric = build_data_fabric()
    for ds in fabric.datasets:
        if not ds.variables:
            continue
        mean_var_missing = sum(v.missing_pct for v in ds.variables) / len(ds.variables)
        assert abs(ds.missingness - round(mean_var_missing, 3)) < 1e-6
        for v in ds.variables:
            assert 0.0 <= v.missing_pct <= 100.0


def test_synthetic_data_is_honestly_tagged_not_observed() -> None:
    """SPEC §34: synthetic city data must never be presented as real/Observed."""
    fabric = build_data_fabric()
    for ds in fabric.datasets:
        if ds.kind == "synthetic":
            assert ds.tag == "Simulated", f"{ds.id} synthetic but tagged {ds.tag}"
        # Real-world names appear only as schema analogues, never as live sources.
        assert ds.publisher.lower().find("synthetic") >= 0 or ds.kind == "assumption-set"


def test_format_support_lists_the_spec4_contract() -> None:
    fabric = build_data_fabric()
    formats = {f.format for f in fabric.format_support}
    # A representative slice of the SPEC §4 supported-format list must be present.
    assert "JSON" in formats
    assert any("GeoJSON" in f for f in formats)
    assert any("GTFS" in f for f in formats)
    assert any("census" in f.lower() for f in formats)
    # Native formats are the ones actually read in the demo.
    native = {f.format for f in fabric.format_support if f.status == "native"}
    assert "JSON" in native


def test_harmonisation_pipeline_is_honest_about_what_runs() -> None:
    """Implemented steps must point to real code; N/A steps must say why."""
    fabric = build_data_fabric()
    steps = {h.step: h for h in fabric.harmonisation}
    # Steps that genuinely run on this data.
    for s in ("geographic joins", "unit normalisation", "population weighting", "provenance tracking"):
        assert steps[s].implemented, f"{s} should be implemented"
        assert steps[s].where
    # Steps that are honestly N/A for a single-snapshot synthetic city.
    for s in ("time alignment", "inflation adjustment"):
        assert not steps[s].implemented
        assert "N/A" in steps[s].where


def test_is_deterministic() -> None:
    """The catalogue must be byte-identical across calls (SPEC §34)."""
    a = client.get("/data-fabric").json()
    b = client.get("/data-fabric").json()
    assert a == b
