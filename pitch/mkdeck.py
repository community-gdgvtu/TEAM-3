import json
L=lambda p: json.load(open(p))
live=L("pipeline_live.json"); var=L("variants.json"); cases=L("division_cases.json")
sweep=L("division_sweep.json"); mlm=L("api/ml_models.json"); reg=L("api/registry.json")
fab=L("api/data-fabric.json"); cap=L("api/capabilities.json"); ch=L("api/parliament_nz_chamber.json")
man=L("/Users/gavinwu/Desktop/Files on Macbook/2026 Files/01 Business/Hackathon/urban-policy-twin/frontend/public/city/osm_manifest.json")
sim=live["simulate"]; cps=sim["delta"]["checkpoints"]
def series(key):
    s=[x for x in sim["delta"]["series"] if x["key"]==key][0]
    return {"label":s["label"],"unit":s["unit"],
            "points":[{"t":c["t_months"],"lbl":c["label"],"pct":p["delta_pct"],"d":p["delta"]}
                      for c,p in zip(cps,s["points"])]}
D={}
D["prompt"]=live["_prompt"]
D["stages"]=live["_stages"]; D["total_ms"]=live["_total_ms"]; D["total_bytes"]=live["_total_bytes"]
D["compiled"]=live["compile"]["policy"]
D["assumptions"]=live["compile"].get("assumptions",[])[:9]
D["compile_method"]=live["compile"].get("method"); D["compile_prov"]=live["compile"].get("provenance")
D["series"]={k:series(k) for k in ["traffic.vehicle_trips_into_cbd","emissions.daily_co2_tonnes",
    "mode_share.car_pct","transit.daily_transit_trips","traffic.daily_vehicle_km",
    "transit.peak_into_cbd_transit_trips","mode_share.public_transit_pct"]}
D["checkpoints"]=cps
# ML
D["ml"]={"lstm":mlm["sequence"]["by_horizon"],"arch":mlm["sequence"]["architecture"],
         "overall":mlm["sequence"]["overall"],"dataset":mlm["dataset"],
         "regressors":[{"name":m["name"],"r2":m["r2"],"mae":m["mae_mph"],"best":m["best"]} for m in mlm["models"]],
         "horizon_minutes":mlm["horizon_minutes"],"target":mlm["target"]}
# spatial
sp=live["spatial"]
D["spatial"]={k:sp[k] for k in ["peak_hour_car_trips_a","peak_hour_car_trips_b","world_a","world_b",
    "cordon_inflow_delta_pct","vehicle_hours_delta_pct","accessibility","pollution","params","note"]}
D["spatial"]["notable_arcs"]=sp["notable_arcs"][:10]
# microsim
ms=live["microsim"]
D["microsim"]={k:ms[k] for k in ["commuters","winners","losers","unaffected","mean_gc_change_min",
    "payers","mean_payer_burden_pct","regressivity_ratio","regressivity_note","constraint_check",
    "worst_hit","biggest_winner","by_income_decile","note"]}
# parliament
D["chamber"]=ch
D["division_carried"]=cases["works, protected"]
D["division_lost"]=cases["no effect, breaches cap"]
D["division_cases"]=cases
D["division_sweep"]=[{k:s[k] for k in ("burden","ayes","noes","abst","passed","equity_harm")} for s in sweep]
D["division_live"]=live["division"]
D["failure_modes"]=live["failure_modes"]["failure_modes"]
# public + media
pub=live["public"]
cs=sorted(pub["cohorts"], key=lambda c:c["distribution"]["net_support"])
D["public"]={"overall":pub["overall"],"population":pub["population"],"n_cohorts":len(pub["cohorts"]),
             "extremes":{"opposed":cs[:5],"supportive":cs[-5:]},"note":pub["note"]}
D["public"]["all_cohorts"]=[{"i":c["income_band"],"g":c["geography"],"m":c["travel_mode"],
                             "n":c["size"],"net":c["distribution"]["net_support"]} for c in pub["cohorts"]]
D["net_support_flat"]=var["flat"]["net_support"]; D["net_support_protected"]=var["protected"]["net_support"]
D["media"]=live["media"]
# analogues, stress, sdg, economy, diffusion
an=live["analogues"]
D["analogues"]={k:an[k] for k in ["estimated_effect_pct","ci_low_pct","ci_high_pct","analogue_quality",
    "transferability_score","metric_label","horizon_label","note"]}
D["analogues"]["cases"]=[{k:c[k] for k in ("case_id","name","year","applicable","did_effect_pct",
    "identification_strength","transferability_score","analogue_quality","pool_weight")} for c in an["cases"]]
st=live["stress"]
D["stress"]={"robustness":st["robustness"],"horizon_label":st["horizon_label"],"note":st["note"],
  "scenarios":[{"label":s["label"],"category":s["category"],"confidence":s["confidence"],
    "metrics":[{"label":m["label"],"retained":m["retained_pct"],"verdict":m["verdict"]} for m in s["metrics"]]}
    for s in st["scenarios"]],
  "baseline":[{"label":m["label"],"pct":m["delta_baseline_pct"],"unit":m["unit"]} for m in st["baseline"]["metrics"]]}
D["sdg"]=live["sdg"]
D["economy"]=live["economy"]
# registry / fabric / capabilities
D["registry"]={"counts":reg["counts"],"app_version":reg["app_version"],
  "guardrails":[{"id":g["id"],"rule":g["rule"],"holds":g["holds"]} for g in reg["guardrails"]],
  "models":[{"id":m["id"],"name":m["name"],"layer":m.get("layer"),"tag":m.get("provenance") or m.get("tag")} for m in reg["models"]]}
D["fabric"]={"counts":fab["counts"],"formats":fab["format_support"],"lineage":fab["lineage_contract"],
  "datasets":[{k:ds.get(k) for k in ("id","title","publisher","kind","tag","record_count","format","revision","license")} for ds in fab["datasets"]]}
D["capabilities"]=cap["counts"]
D["osm"]={"counts":man["counts"],"frontend":man["frontend"]["counts"],"fetched_at":man["fetched_at"],
  "radius_km":man["radius_km"],"bbox":man["bbox"],"height_sources":man["height_sources"],
  "source":man["source"],"elapsed_seconds":man["elapsed_seconds"]}
json.dump(D, open("deck.json","w"))
import os; print("deck.json", round(os.path.getsize("deck.json")/1024), "KB")
print("keys:", ", ".join(D))
