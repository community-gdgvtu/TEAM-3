# Shared demo dataset — Meridia synthetic city grid

**Provenance: `Synthetic`.** This is the common *input world state* for the URBAN
digital twin demo. "Meridia" is a fictional city on a regular 9×9 grid — it is
**not a real place** and contains no real person or administrative record. Only
the WGS84 lon/lat coordinates are real-shaped, so the frontend map
(MapLibre/deck.gl) can render it.

This dataset is **not a simulation result**. Numeric policy effects are produced
later by the simulation engine — never by an LLM (SPEC §34).

## Regenerate

```bash
python data/generate_city.py            # default seed 42 -> data/city/
python data/generate_city.py --seed 7   # different city instance
```

The generator uses only the Python standard library and is fully deterministic
for a fixed seed, so the committed files under `data/city/` reproduce exactly.

## Files (`data/city/`)

| File | Format | Contents |
|------|--------|----------|
| `manifest.json` | JSON | Provenance, grid config, summary counts + totals |
| `zones.geojson` | GeoJSON `FeatureCollection` (Polygon) | Zones with population, jobs, land use |
| `roads.geojson` | GeoJSON `FeatureCollection` (LineString) | Grid road links with capacity/speed + cordon flag |
| `od_pairs.json` | JSON | Origin→destination daily commute trips (gravity) |
| `cbd_polygon.geojson` | GeoJSON `Feature` (Polygon) | The priced/pedestrianised central-district cordon |

### Zone properties

`zone_id`, `row`, `col`, `category` (`cbd`/`inner`/`residential`/`industrial`/`green`),
`land_use`, `is_cbd`, `centroid_lon`, `centroid_lat`, `area_km2`, `population`,
`households`, `jobs`.

### Road link properties

`link_id`, `from_zone`, `to_zone`, `road_class` (`arterial`/`local`), `lanes`,
`length_km`, `capacity_veh_per_hr`, `free_flow_speed_kmh`, `crosses_cordon`
(link enters the CBD from outside — this set forms the congestion-charge
cordon), `interior_cbd`.

### OD pairs

Destination-constrained gravity model: each zone's `jobs` are distributed among
origin zones ∝ `population / distance²`. Inflow to a zone therefore ≈ its jobs,
so the matrix reads as home→work commute flows and trips into the CBD ≈ CBD
jobs. Small pairs (< `min_trips`) are dropped to keep the file lean. Each pair:
`origin`, `destination`, `daily_person_trips`, `distance_km`, `dest_is_cbd`.

## Consuming it

Backend: `backend/app/dataset.py` provides cached loaders
(`load_zones()`, `load_roads()`, `load_od_pairs()`, `load_cbd_polygon()`,
`load_manifest()`) plus helpers `zone_index()` and `cbd_zone_ids()`.
Integrity is covered by `backend/tests/test_dataset.py`.
