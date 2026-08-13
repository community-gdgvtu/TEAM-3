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
