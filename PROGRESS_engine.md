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
- 2026-08-13 — M7 counterfactual comparison: new `backend/app/simulation/counterfactual.py` +
  `POST /compare`. Returns World A (baseline) vs World B (intervention) vs one world per supplied
  amendment (C, D…) in a single payload. Each intervention world carries its snapshot, trajectory,
  Δ-vs-baseline and Δ-vs-intervention (None for B). Plus a headline table: one row per metric with the
  baseline value (never omitted, SPEC §21) and each world's value + Δ + Δ% at a chosen horizon. Amendment
  worlds reuse `apply_amendment` (structured DSL edits only); every number from the same deterministic
  model, no LLM (SPEC §21/§34). Horizon snaps to nearest checkpoint (default 5y). 5 tests; 125 green.
  **M7 complete — Evidence, uncertainty, credibility milestone done.**
- 2026-08-13 — Stretch policy optimiser stub: new `backend/app/optimiser/` package + `POST /optimise`.
  Works the problem backwards (SPEC §22): grid-searches 25 candidate interventions (congestion charge
  across amount × revenue split × low-income exemption, parking levy, pedestrianisation), simulates each
  with the deterministic World-B model and the cohort opinion model, and scores four competing objectives —
  emissions reduction %, size-weighted average commute-cost increase %, size-weighted low-income burden %
  (both real generalized-cost impacts pulled from the opinion cohorts, normalised by a one-pass baseline
  reference gc), and an Estimated scheme-cost proxy — plus net public support for context. Applies the
  supplied objective/constraints (reduce_transport_emissions_pct target, max_average_commute_increase_pct,
  max_low_income_burden_increase_pct, max_budget), builds the feasible 4-objective Pareto frontier, and
  labels representative policies (cheapest / most-equitable / largest-emissions-reduction / best-balanced
  via min-max-normalised distance to the ideal point). Outcome metrics Simulated; only est_cost is a
  documented Estimated constant (used solely for the budget constraint), clearly flagged; unsatisfiable
  constraints are flagged but a frontier over all candidates is still returned so the UI is never empty.
  ~1.2s for the full grid, deterministic, no LLM (SPEC §22/§34). 8 tests; 133 green.
- 2026-08-13 — Stretch backtesting harness scaffold: new `backend/app/backtest/` package +
  `GET /backtest/example` + `POST /backtest`. Historical replay (SPEC §25): takes a HistoricalCase
  (a policy plus its known outcomes + observed event months), replays it through the deterministic
  World-A/B/Δ model + event ledger using only pre-implementation state, and scores the forecast against
  the actuals — forecast error (MAE/RMSE/MAPE via linear interpolation of the World-B trajectory to each
  observation month), direction accuracy (sign of forecast−baseline vs actual−baseline), interval
  calibration (fraction of actuals inside the forecast's uncertainty band), and event-timing error
  (|predicted − actual| month, matched to the ledger by event type). Ships a built-in synthetic
  Meridia-2018 cordon benchmark case whose actuals are clearly labelled Simulated (not real records) so
  the scaffold produces a meaningful non-trivial scorecard end-to-end; geographic + full distributional
  accuracy are explicitly flagged as unscored in the scaffold (no per-zone actuals) rather than silently
  skipped. Forecast Simulated, scores exact arithmetic, deterministic, no LLM (SPEC §25/§34). Perfect-
  actuals ⇒ ~0 error/100% coverage; wrong-sign & out-of-band cases are caught. 7 tests; 140 green.
  **All ENGINE roadmap items (M3–M7 + both stretch) complete.**
- 2026-08-13 — SDG alignment layer (SPEC §23): new `backend/app/sdg/` package + `POST /sdg`.
  Maps a compiled policy onto UN SDG targets using measurable indicators / transparent proxies,
  reading numbers straight from the deterministic World-A/World-B sim, the cohort-opinion
  generalized-cost burden model, and the run's own audit artifacts. **Core** SDG 11 (sustainable
  mode share 11.2; CBD private-vehicle trips 11.2/11.6; peak transit ridership 11.2) and SDG 16
  (share of decision metrics published with full provenance+method+assumptions 16.6/16.10; count of
  structured cause→effect→confidence event-ledger records 16.7 — deliberately governance-*process*
  proxies, not transport outcomes, so URBAN's own contribution to institutional transparency is
  measured, not invented). **Secondary** SDG 13 (transport CO₂ 13.2) and SDG 10 (excess travel-cost
  burden on lowest-income vs average commuters 10.4, from the same burden model the optimiser uses —
  faithfully reports the model even when the answer is progressive/regressive). Every indicator
  carries SPEC §23's mandated shape (indicator/proxy · baseline · scenario · change · data source ·
  confidence), confidence widens with horizon (SPEC §9/§24), and there is **no arbitrary composite
  "SDG score"** (SPEC §23 forbids it) — the report only counts improved/worsened/unchanged. Transport
  indicators tagged Simulated, proxy/opinion-derived ones Estimated, none Generated; fully
  deterministic, no LLM (SPEC §23/§34). Horizon configurable + snapped to nearest checkpoint (default
  5y). 8 tests; 148 green, app boots with 21 routes. Follow-up: SPEC §14 opinion diffusion queued next.
- 2026-08-13 — Social network / opinion diffusion (SPEC §14): new `backend/app/diffusion/` package
  + `POST /diffusion`. Builds an abstract social graph — 5 citizen-cohort nodes (one per income band,
  round-0 opinions seeded size-weighted from the deterministic cohort-opinion model) plus journalists,
  government, opposition, business, influencers, community groups and public institutions (each with a
  transparent, documented opinion prior derived from the policy's own structure: who proposes it, who it
  costs, how the distributional burden falls). Edges are typed (social influence / media exposure /
  geography / workplace / political affinity / institutional) and the incoming-influence matrix is
  row-stochastic per node. Runs a deterministic **Friedkin–Johnsen** diffusion — x_i(t+1) = λ_i·Σ W_ij x_j(t)
  + (1−λ_i)·x_i(0), so each actor drifts toward the weighted opinion of who it listens to while staying
  partly anchored to its own conviction (susceptibility λ by type: citizens/journalists open, politicians
  entrenched) — over N information rounds. Outputs: per-node opinion trajectories, issue salience
  (mean strength of feeling) and opinion polarisation (population-weighted dispersion) per round,
  coalition formation (support / oppose / contested blocs with citizen share + mean opinion), the
  dominant narrative, and citizen net-support drift from round 0 → final. Optional narrative
  **information shocks** (round · node · delta, e.g. a scandal hitting the press or a viral campaign
  hitting influencers) durably shift the target's FJ anchor so the effect propagates instead of washing
  out in one round. Opinions bounded [-1,1]; rounds are information-diffusion steps, explicitly NOT the
  physical Time-Machine horizon (noted in the payload). Fully deterministic, no randomness, no LLM
  (SPEC §14/§34). 9 tests; 157 green, app boots with 22 routes. **SPEC §14 + §23 now covered beyond the
  original M3–M7 + stretch roadmap.**
- 2026-08-13 — Model registry / transparency manifest (SPEC §33): new `backend/app/registry/`
  package + `GET /registry`. A machine-readable "how do we know these numbers aren't AI
  astrology?" answer. Lists every forecast layer (baseline agent-based mode-choice, World-B
  policy sim, Time Machine staged-adaptation timeline, Monte-Carlo uncertainty sweep, cohort
  opinion model, Friedkin–Johnsen opinion diffusion, policy optimiser, Model Parliament,
  simulated media) as a self-describing `ModelCard` — SPEC sections, method paragraph,
  determinism class (deterministic / stochastic-seeded), the provenance tag applied to its
  outputs, its Python module path, and an explicit `llm_touches_numbers` flag that is **False**
  for every numeric layer (LLM confined to prose in parliament/media and language structuring in
  the compiler). Numeric layers publish their documented input assumptions **read live from the
  code** (`DEFAULT_PARAMS`, `DEFAULT_SIM_PARAMS`, `DEFAULT_ADAPTATION`, `OpinionParams` via
  introspection) so the published values can never disagree with what actually runs. Also emits
  data-source cards (synthetic population, baseline assumption set, compiled Policy DSL) and the
  SPEC §34 guardrail checklist (no-LLM-numbers · provenance tags · SIMULATED media · widening
  uncertainty · reproducibility) each with a concrete `enforced_by` and a `holds` flag, plus a
  flat de-duplicated assumption index and summary counts. The registry is tagged **Observed**
  (it describes the code, it is not a simulation output). Fully deterministic, no LLM (SPEC
  §33/§34). 5 tests; 162 green, app boots with 23 routes.
- 2026-08-13 — Press conference simulation (SPEC §16): new `backend/app/press/` package +
  `POST /press-conference`. Stages the moment after a policy is announced: a government
  spokesperson opening statement built from the run's own figures (central-traffic Δ, daily
  commuter-CO₂ Δ, whether revenue is being reinvested) followed by five archetype journalist
  exchanges. Public broadcaster presses on whether the mode-share change matches what was
  promised; the business correspondent challenges delivery/access cost pass-through; the tabloid
  runs the populist "tax on drivers" line quoting the modelled opposition share; the environment
  correspondent argues it isn't ambitious enough on climate; and a local/opposition reporter goes
  at distributional fairness, naming the worst-hit cohort by mean material impact. Every question
  is anchored to a specific Δ metric / event-ledger entry / opinion figure, and every spokesperson
  answer (stance defends / acknowledges / rebuts / commits) cites the same figures and reflects the
  policy's actual low-income exemption + reinvestment. Reuses the `/media` horizon-state reader so
  numbers are copied straight from the deterministic simulation; an optional LLM (`press/llm.py`,
  same preserve-figures-verbatim contract as parliament) polishes prose only, with a template
  fallback that is the tested default when no key is configured. Whole artifact tagged Generated
  with a SIMULATED banner and fictional outlets/reporters only — no real bylines, no invented
  number (SPEC §16/§34). Horizon configurable (default 5 months, snapped to nearest checkpoint).
  5 tests; 167 green, app boots with 24 routes.
- 2026-08-13 — Ensemble forecasting (SPEC §8): new `backend/app/ensemble/` package +
  `POST /ensemble`. SPEC §7 specs a *hybrid* forecast engine and §8 wants those layers pooled
  into an ensemble whose spread is an honest confidence signal. Implements this for the flagship
  outcome — the reduction in vehicle trips entering the central cordon — with three genuinely
  independent estimators: (1) **structural agent-based** (SPEC §7.5), the deterministic World-B
  model's own Δ% at the horizon (Simulated, weight 0.5, ±15% internal range for behavioural-
  parameter uncertainty); (2) **historical-analogue transfer** (SPEC §7.1), a Michaelis–Menten
  saturating transfer function calibrated on real flat-cordon schemes (empirical asymptote ≈ −30%,
  a half-saturation per-one-way charge) scaled by this policy's charge, with a 0.6–1.25× spread
  reflecting London/Stockholm/Milan variation (Estimated; anchors are illustrative, explicitly not
  this city's data; not applicable to a pure car ban); (3) **reduced-form elasticity** (SPEC §7.2),
  a low out-of-pocket price elasticity of cordon car trips (≈ −0.09, range −0.06…−0.13 — low
  precisely because real cordon charges are large vs fuel cost yet only cut ~20–30%) applied to the
  charge as a % of daily car money cost from the baseline snapshot (Estimated; N/A when no charge).
  Pools the applicable methods by renormalised documented weights into a central estimate, a band =
  [min low, max high] across methods, a method-spread disagreement measure (low/moderate/high) and
  a plain-language interpretation. All percentages clamped to the physically valid [−100, 0]%.
  Crucially it does its job honestly: for a strong charge the ABM's ~−90% cordon collapse is far
  more extreme than real analogues (~−18%), so the ensemble reports **high disagreement — treat the
  magnitude as genuinely uncertain**, exactly the caveat SPEC §8 exists to surface. The ensemble
  output is tagged Estimated (a cross-method blend, not one Simulated run); fully deterministic, no
  LLM (SPEC §8/§34). 5 tests; 172 green, app boots with 25 routes.
- 2026-08-13 — Multi-agent institutional layer (SPEC §18): new `backend/app/institutions/`
  package + `POST /institutions/review`. Adds the institutional agents SPEC §18 lists beyond the
  parliament's five personas — **Climate**, **Implementation**, **Legal/Constitutional Research**
  and **Auditor** — each assessing the policy against a professional mandate rather than arguing a
  political stance. It reuses the parliament's `simulate_brief` + `DebateBrief` (imported, not
  edited — parliament files untouched) so all four agents read the identical deterministic evidence
  (Δ metrics + event ledger + provenance). Climate scores the commuter-CO₂ Δ and emissions event
  against decarbonisation (verdict clear at ≥10% cut, otherwise conditional/concern) and flags
  induced-demand rebound. Implementation detects the adaptation-gap (transit capacity exceeded at a
  month earlier than the revenue-funded uplift → concern, with a front-load-interim-capacity
  recommendation) plus car-ban access management (deliveries / emergency / blue-badge). Legal
  reasons purely from policy structure: statutory legal base + proportionality for any charge, an
  indirect-discrimination / proportionality concern when a flat charge carries no low-income or
  resident exemption, and access-rights + consultation duties for pedestrianisation. The Auditor
  assesses the *evidence itself* — every Δ metric model-derived and tagged Simulated (no LLM in the
  numeric path), confidence bands widening to the horizon, and the event-ledger causal trail — and
  clears on process even when the policy's own effect is weak. Each review returns structured
  `Finding`s (severity info/watch/risk/blocker) with citations to specific metrics/events, a
  per-agent `Verdict` (clear/conditional/concern/block), and the panel rolls up to an overall =
  most-severe verdict, a tally and a deterministic synthesis. Review prose is Generated; every
  cited figure is Simulated; no LLM produces a number (SPEC §18/§34). 5 tests; 177 green, app boots
  with 26 routes.
- 2026-08-13 — Verification run: ENGINE roadmap fully complete (all M3/M5/M6/M7 + Stretch + Extended items checked). Full suite green (177 passed), app boots with 26 routes. No new engine items outstanding in ROADMAP_ENGINE.md; nothing implemented this run.
- 2026-08-13 — Verification run (no new items): ENGINE roadmap fully complete (M3/M5/M6/M7 + Stretch + Extended all checked). Re-ran full suite → 177 passed; app boots with 26 routes. Additionally cross-checked the UI↔backend endpoint contract: every path the frontend calls (incl. `/institutions/review`, `/press-conference`, `/compare`, `/ensemble`, `/registry`, `/sdg`, `/diffusion`, `/backtest`, `/optimise`, `/uncertainty`, `/evidence`) is live in `app.main`. No mismatches, no 404 gaps. No backend code changed this run (declined to invent busywork against an exhausted roadmap; SPEC §34 guardrails all still holding).
- 2026-08-13 09:26 UTC — Verification run (no new items): ENGINE roadmap fully complete (M3/M5/M6/M7 + Stretch + Extended all `[x]`; `grep '\[ \]'` → none). Re-ran full suite → **177 passed in ~30s**; app boots with **26 routes** (all SPEC endpoints live: /simulate, /simulate/amend, /compare, /parliament/debate, /parliament/failure-modes, /public, /media, /evidence, /uncertainty, /optimise, /backtest(+/example), /sdg, /institutions/review, /ensemble, /press-conference, /registry, /diffusion, /baseline, /policy/compile). No backend code changed — the roadmap is exhausted and inventing effects/tests against it would violate the "real working code, no busywork" contract. SPEC §34 guardrails all still hold (no LLM in any numeric path; Observed/Estimated/Simulated/Generated tags intact; media SIMULATED; uncertainty widens with horizon).
- 2026-08-13 09:40 UTC — Economic spillover layer (SPEC §7.4): new `backend/app/economy/`
  package (`params.py`, `schema.py`, `model.py`) + `POST /economy`. Fills a genuine SPEC
  coverage gap — the hybrid forecast engine's §7.4 economic layer was the one MVP layer with
  no endpoint (the roadmap's original M3–M7 + Stretch + Extended items were all complete;
  rather than log a 5th empty verification run I implemented this real gap). Reads the
  deterministic mode-choice sim's **Simulated** drivers (cordon-charge revenue, Δ CBD car
  commuters, Σ Δ commuter travel-minutes, a freight-entry proxy) and translates them into five
  transparent input-output / elasticity channels: charge transfer (household discretionary
  withdrawal, −R×MPC), revenue recycling (full collected revenue re-spent at a local fiscal
  multiplier — commuter Simulated + freight Estimated, so both the freight cost and its own
  revenue are balanced), CBD footfall (car-avoidance loss vs pedestrianisation retail-amenity
  uplift — ambiguous sign, shopper demand explicitly unmodelled), business logistics (freight
  charge pass-through, low confidence), and commuter mode-switch travel-time cost (monetised at
  value-of-time = 1/money_to_minutes, consistent with the GC model). Rolls up per-sector
  exposure + a net partial-equilibrium annual estimate with a wide band, clearly Estimated and
  NOT a GDP number. Differentiates policies sensibly (charge+reinvest net-positive, general-fund
  near-neutral, pedestrianisation net-negative). Honest `not_modelled` surface (congestion-relief
  time savings → needs the §7.7 spatial traffic-assignment layer; agglomeration/land-value; firm
  relocation; shopper/tourist demand; labour-market GE; fiscal-multiplier crowding-out). Physical
  drivers Simulated, monetary translation Estimated (SPEC §8); confidence widens with horizon;
  fully deterministic, no LLM in the numeric path (SPEC §7.4/§34). 8 tests; **185 green**, app
  boots with **27 routes**. Follow-up: register the new layer in the §33 model registry so the
  transparency manifest stays complete.
- 2026-08-13 09:46 UTC — Registered the economic spillover layer in the §33 model registry
  (`backend/app/registry/model.py`): new `economic_spillover` ModelCard (SPEC §7.4, output_tag
  Estimated, produces_numbers=True, llm_role none) with its coefficients read **live** from
  `EconParams` via a new `_economy_assumptions()` helper, plus the `no_llm_numbers` guardrail's
  enforced-by list updated to name the economy layer. Keeps the transparency manifest complete
  and drift-free — the registry now catalogues all 10 forecast layers (8 numeric, 0 touching
  numbers with an LLM). 185 green (5 registry tests unchanged — counts derive from the live
  model list, not hardcoded).
