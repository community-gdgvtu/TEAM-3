# PROGRESS — ENGINE track

Dated log of backend/simulation/data work. Newest at the bottom.

- 2026-08-13 — M3 timeline checkpoints: added `backend/app/simulation/timeline.py`
  (`build_world_b_timeline`) projecting World B across T0/1m/3m/5m/1y/2y/5y/10y via
  staged adaptation — a fast behavioural-substitution ramp (A → reinvestment-off B) plus a
  lagged revenue-funded transit-capacity ramp (→ full B), on top of the baseline's exogenous
  demand trend. Confidence band anchored to a fixed per-metric scale so it widens monotonically
  with the horizon (SPEC §9/§24). Added `reinvestment` gate to `compute_world_b`, `WorldBTimeSeries`
  schema, and `test_simulation_timeline.py` (7 tests). All 57 backend tests green; app boots.
- 2026-08-13 — M3 `POST /simulate`: new `backend/app/routers/simulate.py` returns World A + World B
  snapshots & timelines plus Δ(B−A) per metric across all checkpoints (`simulation/compare.py`).
  Added `simulation/shocks.py` — optional fuel-price / transit-fare / background-demand shocks applied
  to BOTH worlds so the delta still isolates the policy; `seed` accepted & echoed (model is
  deterministic). Δ band = the two worlds' bands combined in quadrature. 6 endpoint tests; 63 green.
- 2026-08-13 — M3 event ledger (SPEC §10): `backend/app/simulation/events.py` derives structured
  events deterministically from Δ(B−A): mode_shift, cordon_load, transit_capacity (vs baseline
  peak capacity × headroom), emissions milestone, and the mid-run revenue-funded transit_reinvestment
  ramp (isolated by comparing boardings vs the short-run plateau, so it fires ~12mo not day-one).
  Each event carries cause/affected_agents/confidence(decays with horizon)/downstream/evidence,
  tagged Simulated. Exposed as `event_ledger` on `POST /simulate`. 7 new tests; 70 green. **M3 complete.**
- 2026-08-13 — M5 parliament: new `backend/app/parliament/` package + `POST /parliament/debate`.
  Five personas (Government/Opposition/Equity/Economist/Devil's Advocate) each deterministically
  select evidence (Δ end-state metrics + event-ledger entries) and take a role-appropriate stance;
  `DebateBrief` is the shared read of the sim output. Prose is LLM-polished when a key is set, with a
  deterministic template fallback (no key → method='template') so the endpoint always returns. Every
  quantitative claim cites a Simulated metric/event — no figure invented (SPEC §11/§34). Equity flips
  support↔conditional on presence of a low-income/resident exemption. 8 tests; 78 green.
- 2026-08-13 — M5 amendment loop: `backend/app/simulation/amendment.py` — `Amendment` models a
  structured, auditable DSL mutation (exempt low-income/residents, set/scale charge, set PT revenue
  share); `apply_amendment` returns a new policy leaving the original untouched. `POST /simulate/amend`
  re-simulates original + amended over one baseline and returns each policy's Δ-vs-baseline plus
  Δ(amended−original) isolating the amendment. Generalised `build_delta` to compare two World-B runs.
  E.g. a low-income exemption drops priced commuters 123→100 and nudges car share +1.7pp. 7 tests; 85 green.
- 2026-08-13 — M5 Failure Mode Register: `backend/app/parliament/failure_modes.py` + `POST
  /parliament/failure-modes`. Devil's Advocate critique → structured ranked register: adaptation-gap
  overcrowding, regressive-burden backlash (only when no low-income exemption), charge-revenue erosion,
  and always-present assumption fragility. Each carries risk/mechanism/severity/probability/evidence/
  mitigation; ranked by severity-weight × probability. Provenance split: risk scores Estimated, cited
  evidence Simulated (SPEC §12/§34). Extracted shared `simulate_brief()`. 6 tests; 91 green. **M5 complete.**
- 2026-08-13 — M6 cohort opinion model: new `backend/app/opinion/` package + `POST /public`. Each
  synthetic micro-agent's OWN modelled material impact (World A vs B generalized-cost Δ) + perceived
  fairness (regressivity of unexempted flat charge on low incomes, exemption benefit, transit-reinvestment
  goodwill, car-ban coercion) + income-band ideological prior → latent support → 6-bucket distribution
  (Strong support…Strong oppose + Uncertain, uncertain mass scaled by policy_salience). Aggregated by
  cohort (income band × geography × baseline mode) and overall. Refactored mode-choice to expose
  `mode_options`/`policy_mode_options`/`pick_mode` (reused for material impact). Deterministic, Simulated.
  Sanity: inbound car commuters most opposed, reinvestment-served transit users most supportive. 8 tests; 99 green.
- 2026-08-13 — M6 simulated media generator: new `backend/app/media/` package + `POST /media`.
  Reads ONLY the event ledger + outcome metrics (World A→B Δ) + opinion state; emits archetype
  headlines across 6 fictional-outlet lenses (public-service, business, local, tabloid, transit-advocacy,
  motoring) at Month 5 and Year 2 horizons. Every artifact carries the `SIMULATED — not a real outlet`
  banner, fictional outlet names (no real bylines), and `cited_refs` back to the model outputs it rests on
  (SPEC §15/§34). Deterministic, Generated media clearly labelled SIMULATED. 6 tests; 105 green. **M6 complete.**
- 2026-08-13 — M7 evidence/provenance trace: new `backend/app/evidence/` package + `POST /evidence`.
  Given a compiled policy + metric key, re-runs the deterministic World-A/B/Δ simulation, finds the
  metric's Δ trajectory, and assembles the SPEC §26 causal ladder: input-data (synthetic Meridia world)
  → transform (the behavioural levers that touch this metric — charge raises car generalized cost,
  reinvestment cuts transit cost/raises speed; reinvestment pruned from pure-traffic metrics) →
  mode-choice model → staged adaptation → result (World A→B, isolated Δ, band). Also returns an ASCII
  trace ladder, the equations/parameters (BehaviouralRule levers), named assumptions (adaptation
  time-constants + metric assumptions), illustrative real-world analogues (London 2003 / Stockholm 2007 /
  Singapore ERP / Milan Area C — Observed, explicitly flagged "not a source of any simulated number"),
  citations to the model modules + SPEC, and a horizon-widening confidence derived from the model's own
  uncertainty band. Every number copied from the sim; no LLM on the numeric path (SPEC §34). Unknown key
  → 404 listing valid keys. 7 tests; 112 green. **First M7 item complete.**
- 2026-08-13 — M7 uncertainty engine: new `backend/app/uncertainty/` package + `POST /uncertainty`.
  Turns one deterministic run into a fan of plausible futures. Monte-Carlo: draws each of 8 documented
  uncertain assumptions (money→time mode-switch elasticity, transit service/bus-capacity response,
  reinvestment fare cut, central congestion feedback, transit speed, car running cost, transit fare,
  CO₂ factor) from a triangular(low, default, high) and re-runs the full A/B/Δ pipeline — each sample
  yields the whole Δ trajectory, so the fan across every Time-Machine checkpoint (median + 50/80/95%
  intervals, widening with horizon) comes for free. Sensitivity: one-at-a-time low↔high swing per
  assumption, ranked → most-influential-assumption list with direction. Model disagreement: low/central/
  high behavioural-regime ensemble → spread. Seeded (reproducible), samples clamped 20–500 (~3s at the
  100-sample default). Only documented input assumptions are perturbed and the same structural code is
  re-run; no LLM on the numeric path (SPEC §34). Unknown key → 404. 8 tests; 120 green. **Second M7 item complete.**
