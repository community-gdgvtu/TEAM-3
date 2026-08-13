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
