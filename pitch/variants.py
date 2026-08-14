import json, urllib.request
BASE="http://127.0.0.1:8000"
def call(path, body=None, method=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path, data=data, method=method or ("POST" if data else "GET"),
        headers={"Content-Type":"application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read())

def outcome_from(sim, micro, months=24.0):
    idx=[i for i,c in enumerate(sim["delta"]["checkpoints"]) if c["t_months"]==months][0]
    g=lambda k:[s for s in sim["delta"]["series"] if s["key"]==k][0]["points"][idx]["delta_pct"]
    return {
      "car_trips_into_cbd_pct": round(g("traffic.vehicle_trips_into_cbd"),2),
      "co2_pct": round(g("emissions.daily_co2_tonnes"),2),
      "congestion_pct": round(g("traffic.daily_vehicle_km"),2),
      "transit_trips_pct": round(g("transit.daily_transit_trips"),2),
      "low_income_burden_pct": round(micro["by_income_decile"][0]["mean_burden_pct_income"],3),
    }

PROMPTS = {
 "protected": ("Introduce a charge of 12 credits on private vehicles entering the central business district "
   "between 7am and 7pm on weekdays, starting 2026-01-01. Exempt buses, taxis, and blue-badge holders. "
   "Spend 70% of the revenue on public transport and 20% on cycling and walking. The aim is to cut congestion "
   "and emissions without raising costs for low-income residents by more than 5%."),
 "flat": ("Introduce a charge of 30 credits on every vehicle entering the central business district at any hour, "
   "every day, starting 2026-01-01. There are no exemptions. All revenue goes to the general fund. "
   "The aim is to cut congestion and raise revenue."),
}
out={}
for name,prompt in PROMPTS.items():
    comp=call("/policy/compile",{"text":prompt}); pol=comp["policy"]
    sim=call("/simulate",{"policy":pol}); micro=call("/microsim",{"policy":pol})
    oc=outcome_from(sim,micro)
    div=call("/parliament/nz/division",{"policy":pol,"outcome":oc})
    pub=call("/public",{"policy":pol})
    out[name]={"compiled":comp,"outcome":oc,"division":div,
               "constraint":micro.get("constraint_check"),
               "regressivity":micro["regressivity_ratio"],
               "net_support":pub["overall"]["net_support"],
               "deciles":micro["by_income_decile"]}
    r=div["result"]
    print(f"{name:10s} ayes={r['ayes']:3d} noes={r['noes']:3d} abst={r['abstentions']:3d} passed={r['passed']}  "
          f"burden={oc['low_income_burden_pct']}%  cap_ok={(micro.get('constraint_check') or {}).get('satisfied')}  net_support={pub['overall']['net_support']}")
    for b in div["divisions"]:
        print(f"    {b['short']:14s} {b['stance']:8s} ayes={b['ayes']:3d} noes={b['noes']:3d} abs={b['abstentions']:3d}")
json.dump(out, open("variants.json","w"))
