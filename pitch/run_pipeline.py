import json, time, urllib.request

BASE = "http://127.0.0.1:8000"
PROMPT = ("Introduce a charge of 12 credits on private vehicles entering the central "
 "business district between 7am and 7pm on weekdays, starting 2026-01-01. "
 "Exempt buses, taxis, and blue-badge holders. Spend 70% of the revenue on "
 "public transport and 20% on cycling and walking. The aim is to cut "
 "congestion and emissions without raising costs for low-income residents by "
 "more than 5%.")

def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
    ms = (time.perf_counter() - t0) * 1000
    return json.loads(raw), len(raw), ms

stages = []
out = {}

def stage(sid, label, method, path, body=None):
    d, b, ms = call(method, path, body)
    stages.append({"id": sid, "label": label, "path": path, "method": method,
                   "bytes": b, "ms": round(ms)})
    out[sid] = d
    print(f"{sid:10s} {round(ms):6d} ms  {b:8d} B  {path}")
    return d

T0 = time.perf_counter()
comp = stage("compile", "Policy compiled", "POST", "/policy/compile", {"text": PROMPT})
policy = comp["policy"]

# datasets — parallel in the UI; measured together here
t = time.perf_counter()
sensors, sb, _ = call("GET", "/ml/sensors")
base, bb, _ = call("GET", "/baseline")
ms = (time.perf_counter() - t) * 1000
stages.append({"id": "datasets", "label": "Datasets loaded", "path": "/ml/sensors + /baseline",
               "method": "GET", "bytes": sb + bb, "ms": round(ms)})
out["sensors"] = sensors; out["baseline"] = base
print(f"{'datasets':10s} {round(ms):6d} ms  {sb+bb:8d} B")

stage("models", "Models loaded", "GET", "/ml/models")
stage("forecast", "Prediction generated", "GET", "/ml/forecast/example")
stage("simulate", "Simulation complete", "POST", "/simulate", {"policy": policy})
stage("public", "Public reaction modelled", "POST", "/public", {"policy": policy})
stage("division", "Division simulated", "POST", "/parliament/nz/division", {"policy": policy})
stage("media", "Coverage generated", "POST", "/media", {"policy": policy})
total_ms = round((time.perf_counter() - T0) * 1000)

# extra engines the deck slides need
for sid, path in [("microsim", "/microsim"), ("spatial", "/spatial"), ("sdg", "/sdg"),
                  ("economy", "/economy"), ("analogues", "/analogues"),
                  ("uncertainty", "/uncertainty"), ("stress", "/stress-test"),
                  ("failure_modes", "/parliament/failure-modes"), ("diffusion", "/diffusion")]:
    try:
        d, b, ms = call("POST", path, {"policy": policy})
        out[sid] = d
        print(f"{sid:10s} {round(ms):6d} ms  {b:8d} B  {path}")
    except Exception as e:
        print(f"{sid:10s} FAILED {e}")

out["_stages"] = stages
out["_total_ms"] = total_ms
out["_total_bytes"] = sum(s["bytes"] for s in stages)
out["_prompt"] = PROMPT
print("TOTAL", total_ms, "ms", out["_total_bytes"], "bytes")
json.dump(out, open("pipeline_live.json", "w"))
