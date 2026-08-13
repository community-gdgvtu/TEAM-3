# PROGRESS — ENGINE track

Dated log of backend/simulation/data work. Newest at the bottom.

- 2026-08-13 — M3 timeline checkpoints: added `backend/app/simulation/timeline.py`
  (`build_world_b_timeline`) projecting World B across T0/1m/3m/5m/1y/2y/5y/10y via
  staged adaptation — a fast behavioural-substitution ramp (A → reinvestment-off B) plus a
  lagged revenue-funded transit-capacity ramp (→ full B), on top of the baseline's exogenous
  demand trend. Confidence band anchored to a fixed per-metric scale so it widens monotonically
  with the horizon (SPEC §9/§24). Added `reinvestment` gate to `compute_world_b`, `WorldBTimeSeries`
  schema, and `test_simulation_timeline.py` (7 tests). All 57 backend tests green; app boots.
