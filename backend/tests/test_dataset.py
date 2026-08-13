"""Integrity checks for the shared synthetic city dataset (``data/city``).

These assert structural consistency (referential integrity, provenance tags,
geometry validity) rather than exact numbers, so they stay stable if the
generator is re-tuned.
"""

from __future__ import annotations

from app import dataset


def test_manifest_is_synthetic_and_counts_present() -> None:
    m = dataset.load_manifest()
    assert m["provenance"] == "Synthetic"
    counts = m["counts"]
    assert counts["zones"] > 0
    assert counts["od_pairs"] > 0
    # generator advertises where it came from
    assert m["generated_by"].endswith("generate_city.py")


def test_zone_count_matches_grid() -> None:
    m = dataset.load_manifest()
    grid = m["grid"]
    features = dataset.load_zones()["features"]
    assert len(features) == grid["rows"] * grid["cols"] == m["counts"]["zones"]


def test_zone_ids_unique_and_polygons_closed() -> None:
    features = dataset.load_zones()["features"]
    ids = [f["properties"]["zone_id"] for f in features]
    assert len(ids) == len(set(ids))
    for f in features:
        ring = f["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1], "polygon ring must be closed"
        assert len(ring) == 5, "square zone cell has 4 corners + closure"


def test_cbd_zones_present_and_flagged() -> None:
    cbd = dataset.cbd_zone_ids()
    assert cbd, "expected a central district"
    idx = dataset.zone_index()
    for zid in cbd:
        assert idx[zid]["is_cbd"] is True


def test_roads_reference_real_zones_and_have_capacity() -> None:
    zones = set(dataset.zone_index())
    for f in dataset.load_roads()["features"]:
        p = f["properties"]
        assert p["from_zone"] in zones
        assert p["to_zone"] in zones
        assert p["capacity_veh_per_hr"] > 0
        assert p["length_km"] > 0
        coords = f["geometry"]["coordinates"]
        assert len(coords) == 2, "link is a two-point segment"


def test_cordon_links_exist_for_priced_district() -> None:
    crossing = [
        f for f in dataset.load_roads()["features"]
        if f["properties"]["crosses_cordon"]
    ]
    assert crossing, "priced district needs cordon-crossing links"


def test_od_pairs_reference_real_zones_and_positive_trips() -> None:
    zones = set(dataset.zone_index())
    od = dataset.load_od_pairs()
    assert od["units"] == "daily_person_trips"
    for pair in od["pairs"]:
        assert pair["origin"] in zones
        assert pair["destination"] in zones
        assert pair["origin"] != pair["destination"]
        assert pair["daily_person_trips"] > 0


def test_cbd_polygon_matches_flagged_zones() -> None:
    poly = dataset.load_cbd_polygon()
    assert poly["geometry"]["type"] == "Polygon"
    ring = poly["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert set(poly["properties"]["zone_ids"]) == dataset.cbd_zone_ids()
