import json, math, os
CITY = "/Users/gavinwu/Desktop/Files on Macbook/2026 Files/01 Business/Hackathon/urban-policy-twin/frontend/public/city"
L = lambda n: json.load(open(os.path.join(CITY, n)))
man = L("osm_manifest.json"); bb = man["bbox"]
W, H = 1400, 1000
lat0 = math.radians((bb["north"] + bb["south"]) / 2)
def merc(lon, lat):
    x = (lon - bb["west"]) / (bb["east"] - bb["west"])
    y = (bb["north"] - lat) / (bb["north"] - bb["south"])
    return x, y
# preserve aspect
aspect = ((bb["east"]-bb["west"]) * math.cos(lat0)) / (bb["north"]-bb["south"])
H = round(W / aspect)
def P(lon, lat):
    x, y = merc(lon, lat)
    return f"{x*W:.1f} {y*H:.1f}"
def line(coords):
    pts = [P(c[0], c[1]) for c in coords]
    out, prev = [], None
    for p in pts:
        if p != prev: out.append(p); prev = p
    if len(out) < 2: return ""
    return "M" + "L".join(out)
def poly(geom):
    t = geom["type"]
    if t == "LineString":
        return line(geom["coordinates"])
    if t == "MultiLineString":
        return "".join(line(s) for s in geom["coordinates"])
    rings = geom["coordinates"] if t == "Polygon" else [r for p in geom["coordinates"] for r in p]
    d = ""
    for ring in rings:
        pts = [P(c[0], c[1]) for c in ring]
        out, prev = [], None
        for p in pts:
            if p != prev: out.append(p); prev = p
        if len(out) > 2: d += "M" + "L".join(out) + "Z"
    return d

# --- water & parks
water = "".join(poly(f["geometry"]) for f in L("osm_water.geojson")["features"])
lu = L("osm_landuse.geojson")["features"]
parks = "".join(poly(f["geometry"]) for f in lu if (f["properties"].get("kind") in ("park","grass","forest","recreation_ground","garden","pitch","cemetery")))

# --- roads by class
roads = L("osm_roads.geojson")["features"]
byclass = {}
for f in roads:
    c = f["properties"].get("c", "local")
    g = f["geometry"]
    segs = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
    for s in segs:
        d = line(s)
        if d: byclass.setdefault(c, []).append(d)
road_paths = {c: "".join(v) for c, v in byclass.items()}

# --- cordon + zones
cbd = L("cbd_polygon.geojson")
cordon = poly(cbd["geometry"])
zones = L("zones.geojson")["features"]

spatial = json.load(open("pipeline_live.json"))["spatial"]
drops = {d["zone_id"]: d for d in spatial["pollution"]["biggest_drops"]}
cbd_ids = set(cbd["properties"]["zone_ids"])
zone_paths = []
for f in zones:
    zid = f["properties"]["zone_id"]
    zone_paths.append({"id": zid, "d": poly(f["geometry"]), "is_cbd": f["properties"]["is_cbd"],
                       "pop": f["properties"]["population"], "jobs": f["properties"]["jobs"],
                       "drop_pct": drops.get(zid, {}).get("delta_pct")})

out = {"w": W, "h": H, "water": water, "parks": parks, "roads": road_paths,
       "cordon": cordon, "zones": zone_paths, "bbox": bb,
       "counts": man["frontend"]["counts"], "full_counts": man["counts"],
       "fetched_at": man["fetched_at"], "height_sources": man["height_sources"]}
json.dump(out, open("map.json", "w"))
for k, v in road_paths.items(): print(k, len(v))
print("water", len(water), "parks", len(parks), "cordon", len(cordon))
print("total KB", round(sum(len(v) for v in road_paths.values())/1024 + len(water)/1024 + len(parks)/1024))
print("viewBox", W, H)
