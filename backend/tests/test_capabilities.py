"""Tests for the service capability manifest (GET /capabilities).

The load-bearing guarantee is *reconciliation*: the curated catalogue must match
the live route surface exactly, so a new route without a card (or a card for a
deleted route) fails here rather than shipping an inaccurate manifest.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.baseline.schema import MetricTag
from backend.app.capabilities.catalogue import INFRA_PATHS
from backend.app.capabilities.model import live_route_methods
from backend.app.main import app

client = TestClient(app)

_ALLOWED_TAGS = {t.value for t in MetricTag}


def test_capabilities_served_and_observed() -> None:
    r = client.get("/capabilities")
    assert r.status_code == 200
    m = r.json()
    assert m["provenance"] == "Observed"
    assert m["app_version"]
    assert m["groups"], "manifest must describe at least one area"


def test_catalogue_reconciles_with_live_surface() -> None:
    """Every live product route has a card and every card a live route."""
    m = client.get("/capabilities").json()
    assert m["undocumented_routes"] == [], (
        "live routes with no capability card: " + repr(m["undocumented_routes"])
    )
    assert m["phantom_cards"] == [], (
        "capability cards for routes that don't exist: " + repr(m["phantom_cards"])
    )


def test_every_product_route_is_carded_exactly_once() -> None:
    """The manifest covers exactly the live product surface (infra excluded)."""
    live = set(live_route_methods(app))
    carded = {
        ep["path"]
        for g in client.get("/capabilities").json()["groups"]
        for ep in g["endpoints"]
    }
    assert carded == live
    # Framework docs infra is deliberately not described.
    assert not (carded & INFRA_PATHS)


def test_methods_and_needs_body_match_live() -> None:
    live = live_route_methods(app)
    for g in client.get("/capabilities").json()["groups"]:
        for ep in g["endpoints"]:
            assert ep["methods"] == live[ep["path"]]
            assert ep["needs_body"] == ("POST" in ep["methods"])


def test_output_tags_are_valid_or_null() -> None:
    for g in client.get("/capabilities").json()["groups"]:
        for ep in g["endpoints"]:
            tag = ep["output_tag"]
            assert tag is None or tag in _ALLOWED_TAGS


def test_keyless_examples_are_real_get_routes() -> None:
    m = client.get("/capabilities").json()
    live = live_route_methods(app)
    for path in m["keyless_examples"]:
        assert path in live and "GET" in live[path]
    # Each declared POST→GET companion resolves to a served GET.
    for g in m["groups"]:
        for ep in g["endpoints"]:
            comp = ep["keyless_example"]
            if comp is not None:
                assert comp in live and "GET" in live[comp]


def test_root_advertises_capabilities() -> None:
    root = client.get("/").json()
    assert root["capabilities"] == "/capabilities"


def test_capabilities_is_deterministic() -> None:
    a = client.get("/capabilities").json()
    b = client.get("/capabilities").json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_spec_sections_cover_core_layers() -> None:
    """A few load-bearing SPEC sections must appear somewhere in the map."""
    m = client.get("/capabilities").json()
    seen = {s for g in m["groups"] for ep in g["endpoints"] for s in ep["spec_sections"]}
    for section in ("§7.5", "§9", "§11", "§21", "§34.10", "§37"):
        assert section in seen, f"{section} missing from the capability map"
