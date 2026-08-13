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
- 2026-08-13 09:58 UTC — Built the **System Dynamics / recursive-feedback layer**
  (SPEC §7.6 + §19): new `backend/app/dynamics/` package (`params.py`, `schema.py`,
  `model.py`), `POST /dynamics`, registered in the §33 model registry. This fills the
  one genuinely missing engine capability — the whole roadmap (M3–M7 + Stretch +
  Extended, incl. last run's §7.4 economy layer) was complete, but nothing *closed the
  loop* SPEC §19 calls "central to the concept": World-B is a single adapted end-state
  and the Time Machine is a staged interpolation toward it — neither lets public opinion
  feed back into the **policy itself**. The new layer integrates four coupled stocks
  month-by-month over the 10-yr horizon — charge, transit demand, transit capacity,
  public support — instantiating the exact §19 cascade: charge → mode shift → revenue →
  funded capacity, and sustained negative support → an **endogenous amendment** that cuts
  the charge → weaker price signal → less revenue → slower capacity expansion → renewed
  crowding. Every magnitude each stock chases is read from the deterministic ABM at the
  in-force charge (behavioural-only World-B peak transit demand; priced-commuter annual
  revenue; cohort-opinion net support), memoised per distinct charge so a run costs only a
  handful of ABM evaluations; the temporal coefficients coupling them (relaxation taus,
  capacity build lag, crowding penalty, political threshold/patience/cut-factor) live in
  `SystemDynamicsParams` as documented **Estimated** inputs. Capacity is a genuine
  revenue-funded supply stock — the programme is scoped at announcement to N years of
  *nominal* reinvestment, so if the charge is later cut the plan's cost stays fixed and
  completion stalls (the mechanical heart of the §19 loop). Output: coupled stock
  trajectories at the Time-Machine checkpoints, structured feedback events
  (capacity_exceeded / amendment / crowding_relieved, each carrying its causal chain), and
  — always — a **closed-loop vs open-loop contrast** (political response ON vs OFF, same
  deterministic model) that concretely shows the feedback changes the outcome: the demo £12
  full-reinvest charge is popular at nominal (+0.13 net support) but crowding drives support
  negative, triggering 2 amendments (£12→£7.2→£4.32) and ending at +0.23 support / −0.37
  crowding vs the open-loop run. Edge cases verified: full reinvestment expands peak capacity
  while a general-fund split never does; pedestrianisation (no charge) has an inert political
  arm but still tracks crowding; fully deterministic (identical dumps). Structural anchors
  Simulated, dynamics coefficients Estimated; confidence widens with horizon; no LLM in the
  numeric path (SPEC §7.6/§19/§34). Registry now catalogues 11 forecast layers and the
  no-LLM-numbers guardrail names the new layer. 8 tests; **193 green**, app boots with **28
  routes**. Honest `not_modelled`: continuous charge optimisation (amendments are discrete
  cuts), ridership suppression from crowding (demand stays latent, crowding hits support
  only), capacity depreciation, horizon shocks, spatial/per-corridor detail (needs §7.7).
- 2026-08-13 10:09 UTC — **Verification run — engine roadmap complete.** No unchecked
  items remain in `ROADMAP_ENGINE.md` (M3, M5–M7, Stretch, and every Extended SPEC-coverage
  layer are `[x]`). Confirmed the tree is healthy for this run: full backend suite **193
  passed** (~32s), FastAPI app boots clean with **28 routes**, and smoke checks of the core
  deterministic endpoints pass — `POST /simulate` → 200 with an `event_ledger`, `GET
  /registry` → 200 cataloguing **11 forecast layers** (all asserting no-LLM-in-numbers per
  SPEC §34). Nothing actionable left on this track without new SPEC scope; not scope-creeping
  into speculative features (would risk the §34 guardrails and collide with the UI track /
  shared files this track must not edit). Held to the loop contract: verify + record, release
  the lock. Backend is in a clean, demo-ready state.

- 2026-08-13 10:30 UTC — **Spatial traffic-assignment layer (SPEC §7.7)** —
  `backend/app/spatial/` + `POST /spatial`. This is the explicit-geography layer
  §7.7 asks for and the single gap every other engine layer left open (economy,
  dynamics, ensemble all flag "needs §7.7 / spatial traffic assignment / per-
  corridor detail"). It closes it with a real network model, not a placeholder.
  **Network** (`network.py`): a directed graph built live from the shared Meridia
  grid (`roads.geojson` — 81 zones, 144 undirected links → 288 directed arcs, each
  carrying its per-direction `capacity_veh_per_hr`, free-flow speed and length),
  with a BPR volume-delay function and a Dijkstra shortest-path tree.
  **Assignment** (`assignment.py`): a peak-hour **static user-equilibrium** solved
  by Method of Successive Averages over all-or-nothing loadings (x_k = x_{k-1} +
  (1/k)(y_k − x_{k-1})), so drivers re-route around congestion — the spatial effect
  the aggregate ABM cannot see. Deterministic (identical flows every run).
  **Demand** (`model.py`): generated by the *same* mode-choice model as `/simulate`
  — every synthetic commuter is re-evaluated (World A `choose_mode`, World B
  `choose_mode_policy` with the policy levers) and only those still driving load
  their home→work trip onto the network, so the spatial split can never contradict
  the ABM (SPEC §34). Sample trips are expanded to city scale by a **representation
  factor derived live from the OD table** (≈18.1 = 144.7k commute flows ÷ ~8k
  sampled agents) so peak-hour link volumes are comparable with real-scale road
  capacities; a peak-hour concentration and car occupancy (documented Estimated
  inputs in `params.py`) convert persons→vehicles. **Read-out** per world + Δ:
  congested link flows / v/c / speeds; **cordon inflow** (peak veh/hr entering the
  CBD); total network **vehicle-hours** and vehicle-km; gravity **job accessibility**
  (Aᵢ = Σⱼ jobsⱼ·exp(−decay·congested_timeᵢⱼ)) by congested car time with the biggest
  gaining/losing zones; and a per-zone **road-CO₂ dispersion proxy** (arc veh-km ×
  CO₂ factor, split to endpoint zones, neighbour-smoothed) that shows where central
  pollution falls and whether deterred traffic is displaced outward; plus notable
  arcs (cordon crossings + biggest reroutes) and over-capacity bottleneck lists.
  On the demo £12 full-reinvest charge: cordon inflow −89.6% (9768→1015 veh/hr),
  network vehicle-hours −41.4%, central-CBD CO₂ −80%, job accessibility +0.2%, mean
  congested speed 47.4→49.3 km/h; a no-op (transit-investment, no charge/ban) policy
  leaves the network byte-identical A=B; pedestrianisation collapses cordon inflow
  further than the charge. Runs in ~0.2s. All numbers Simulated, spatial coefficients
  Estimated; fully deterministic, no LLM in the numeric path (SPEC §7.7/§34).
  Registered in the §33 model registry (now **12 forecast layers**, 10 numeric, 0
  touching numbers with an LLM) and named in the no-LLM-numbers guardrail. Honest
  `not_modelled`: single AM inbound peak only (no time-of-day, freight or non-commute
  trips); static within-day equilibrium (no departure-time choice / day-to-day
  learning); pedestrianisation applied demand-side only (no physical road-closure
  through-traffic rerouting imposed on the graph); the CO₂ field is a crude
  neighbour-smoothed dispersion *proxy*, not an air-quality plume model; only the
  road network is spatially assigned (transit is not). New files: `spatial/params.py`,
  `spatial/network.py`, `spatial/assignment.py`, `spatial/model.py`, `spatial/schema.py`,
  `spatial/__init__.py`, `routers/spatial.py`; registry + `main.py` wired.
  **9 new tests; 202 green** (was 193), app boots with **29 routes** (was 28).

- 2026-08-13 10:42 UTC — **Distributional microsimulation layer (SPEC §7.3)** —
  `backend/app/microsim/` + `POST /microsim`. SPEC §7.3 asks the microsimulation
  layer, by name, to answer *Who gains? Who loses? By how much? Which decile? Which
  neighbourhood? Which household type?* — and nothing answered it directly: the
  cohort-opinion model produces a Likert **support** distribution and the optimiser
  a single low-income-burden %, but neither is a £-and-minutes who-gains/who-loses
  microdata table. This computes, for every synthetic commuter, the change in their
  **minimum generalized cost** between World A and World B under the *same*
  deterministic mode-choice model as `/simulate` (World A `mode_options`, World B
  `policy_mode_options`, taking the argmin each side) — so a commuter who
  re-optimises is credited with the cost of their **new** best option, a proper
  discrete-choice welfare change, not a counterfactual they'd never take — plus the
  out-of-pocket charge each agent actually pays. It rolls the person-level impact up
  across **income deciles** (ranked live from synthetic incomes), **household size**
  (1/2/3/4+), **home neighbourhood** (central-vs-outer + the most-adversely-affected
  zones) and **occupation**. Each group carries mean gc-change (minutes-equiv), a
  money-equivalent (Estimated, via the population value-of-time `money_to_minutes`),
  mean charge paid/day, mean annual-charge **burden as % of income**, and
  %worse-off / %better-off / %switched-mode. Headline: winners vs losers vs
  unaffected, count of charge payers + their mean burden, and a **regressivity
  ratio** = bottom-decile burden ÷ top-decile burden with a plain-language verdict,
  plus named worst-hit and biggest-winner groups. Demo £12 full-reinvest charge:
  **1438 winners** (transit users gaining from the reinvested service) / **1679
  losers** / 4868 unaffected; the flat charge is **3.6× regressive** on out-of-pocket
  burden (bottom vs top decile) — yet *more* high-income commuters are worse off
  overall because they drive more, and the report surfaces both dimensions rather
  than collapsing them. Edge cases verified: a low-income exemption zeroes the
  bottom-decile burden (regressivity→0); a general-fund charge (no reinvestment)
  yields **0** transit winners vs 1438 with reinvestment; a no-op transit-investment
  policy leaves everyone unaffected (winners=losers=payers=0); every commuter lands
  in exactly one decile (partition checked). Welfare change Simulated, the
  money-equivalent Estimated (documented population value-of-time; the per-agent GC
  already weights money by each agent's own price sensitivity); fully deterministic,
  no LLM (SPEC §7.3/§34). Registered in the §33 model registry (now **13 forecast
  layers**, 11 numeric, 0 touching numbers with an LLM) and named in the
  no-LLM-numbers guardrail. Honest `not_modelled`: commuter travel welfare only (no
  wider household budgets, labour-supply changes, business costs, or in-kind gains
  from reinvested revenue attributed back to individuals); a single population
  value-of-time (true compensating variation is agent-specific, only approximated);
  no tax/benefit interaction; deciles/household/occupation are the synthetic sample,
  not a real administrative microdata register. New files: `microsim/schema.py`,
  `microsim/model.py`, `microsim/__init__.py`, `routers/microsim.py`; registry +
  `main.py` wired. **8 new tests; 210 green** (was 202), app boots with **30 routes**
  (was 29).

## 2026-08-13 — Verification run (roadmap complete)
- ROADMAP_ENGINE.md fully complete: 24/24 items `[x]`, 0 unchecked across M3/M5/M6/M7
  + Stretch + Extended (SDG, institutions, ensemble, press, registry, economy,
  dynamics, microsim, spatial, diffusion).
- Health check this run: `pytest` **210 passed**; `app.main:app` boots with **30 routes**.
- No actionable engine items remain; owned scope (`backend/**`, `data/**`, `scripts/**`)
  is stable. Did not scope-creep into UI/shared files per parallel-track contract.

## 2026-08-13 (run 10:49 UTC) — SPEC §32 reproducibility manifest (REPRODUCE RUN)
- Roadmap was fully checked (24/24) and the last two runs were no-op verification
  commits. Rather than repeat that, closed a genuine **SPEC §32** gap: determinism
  was asserted everywhere but no endpoint produced the per-run provenance envelope
  behind the "REPRODUCE RUN" affordance (dataset/model versions, params, seed,
  prompts, DSL, assumptions, code version, timestamp).
- Added `backend/app/reproduce/` (`schema.py`, `manifest.py`) + `POST /reproduce`
  (`backend/app/routers/reproduce.py`), wired in `main.py`.
  - `run_id` = SHA-256 content address over the reproducing inputs (policy DSL,
    shocks, seed, **byte-hash of each dataset file**, live assumption index from the
    §33 registry, app + git `code_version`); **timestamp excluded** so identical
    inputs → identical `run_id`.
  - Reproducibility is *proven*: the deterministic A/B/Δ core runs twice and
    `reproducible` is only true when the two `output_digest`s match.
  - `prompts: []` + every model card `llm_touches_numbers: false` (SPEC §34).
  - §33 registry left untouched (per-run record ≠ static catalogue).
- Tests: `backend/tests/test_reproduce.py` (8) — stable/changing run_id, seed in
  identity but not in numbers, content-addressed datasets, shocks in identity,
  no-LLM assertion.
- Health check this run: `pytest` **218 passed** (+8); `app.main:app` boots with
  **31 routes**; new `/reproduce` verified end-to-end (run_id stable, reproducible=true).

## 2026-08-13 (run 11:01 UTC) — SPEC §20 stress-testing environment (POST /stress-test)
- Roadmap was fully checked (25/25) and the prior run had already closed the last
  genuine gap (§32). Rather than a no-op verification commit, closed the next real
  SPEC gap: **§20 external shocks / stress-testing**. The `Shocks` primitive existed
  but only as three raw multipliers passed through `/simulate`; nothing exposed the
  named SPEC §20 toggles or the "holds under X, fails under Y" robustness read-out
  that §20 explicitly calls the point of the feature.
- Added `backend/app/stress/` (`catalogue.py`, `schema.py`, `model.py`) +
  `POST /stress-test` and `GET /stress-test/catalogue` (`backend/app/routers/stress.py`),
  wired in `main.py`.
  - Catalogue = the exact SPEC §20 shock set (recession, fuel-price spike, flood,
    heatwave, population growth, migration change, technology adoption,
    interest-rate shock), each mapped to documented `Shocks` knobs with a rationale
    (SPEC §20: scenario assumptions, not secretly random events).
  - Re-runs the same deterministic A/B/Δ core as `/simulate` per scenario, shock
    applied to BOTH worlds so Δ(B−A) still isolates the policy (SPEC §21). Compares
    the policy's benefit on 4 headline metrics under each shock vs the no-shock
    baseline → per-metric verdict (robust/strengthened/weakened/neutralised/reversed),
    % benefit retained, per-scenario holds/degrades/fails, and an overall
    robust_to / degrades_under / fails_under split.
  - Honest fidelity per SPEC §34: each scenario declares modelled/partial/proxy +
    a caveat. Directly-modelled (fuel spike, demand-growth shocks) vs proxies
    (flood/heatwave/interest-rate) the static commuter model represents weakly —
    interest-rate bite really lives in the §7.4 economy layer; tech scenario
    under-states CO₂ (tailpipe factor held constant). Confidence widens at long
    horizons (SPEC §24).
  - Policy deltas Simulated, shock magnitudes Estimated; deterministic, no LLM.
    404 lists valid scenario keys. Registry (§33) left untouched — stress-test is a
    scenario harness over existing layers (like /uncertainty, /compare), not a new
    numeric model.
- Tests: `backend/tests/test_stress.py` (9) — catalogue completeness, all-scenarios
  run, shock actually moves the world, subset+horizon selection, 404 on bad key,
  the full robust→reversed verdict classifier, retained% consistency, determinism,
  transparent overrides.
- Health check this run: `pytest` **227 passed** (+9); `app.main:app` boots with
  **33 routes** (+2); `/stress-test` verified end-to-end (£12 charge robust to all
  8 shocks, as expected given the large cordon effect).

## 2026-08-13 — Full-pipeline integration smoke test (Hardening, SPEC §3/§34)
- Roadmap was fully complete on entry (all 26 items ✓; 227 tests, 33 routes, boots).
  Rather than bolt on marginal numeric layers into a green codebase near demo time,
  added the one guard the suite lacked: a whole-engine HTTP smoke test.
- `backend/tests/test_integration_smoke.py`:
  - Compiles the SPEC §28 demo policy ONCE (NL→DSL via `/policy/compile`), then
    drives that single compiled DSL through **all 33 routes** (5 GET + 22 POST,
    incl. `/simulate/amend`, `/compare`, `/optimise`, `/uncertainty`, `/backtest`,
    `/reproduce`, `/dynamics`, `/spatial`, `/microsim`, `/press-conference`, …).
    Every route must return 200 — catches cross-layer contract drift (a shared
    Policy-DSL / `Shocks` / metric-key change that 500s a downstream endpoint whose
    own test file never re-runs against the live app). This is the failure mode the
    per-layer unit tests structurally can't see.
  - Enforces SPEC §34 in ONE place, globally: recursively walks every response and
    asserts each `provenance` field references ≥1 allowed tag
    (Observed/Estimated/Simulated/Generated). Surfaced (and accepts) the two valid
    styles across layers — bare enum ("Simulated") and descriptive sentence that
    embeds tags ("ABM anchors Simulated; dynamics coefficients Estimated").
  - Plus targeted invariants: `/simulate` is Simulated with Δ=B−A pointwise across
    checkpoints; `/policy/compile` is Generated; EVERY registry model asserts
    `llm_touches_numbers == False` (no LLM in the numeric path); `/media` carries
    the mandatory SIMULATED banner.
- Pure test-track addition — no `backend/app/**` behaviour changed.
- Health check this run: `pytest` **232 passed** (+5); `app.main:app` boots with
  **33 routes**; whole engine verified end-to-end against the demo policy.

## 2026-08-13 — Determinism regression guard (Hardening, SPEC §24/§34)
- `backend/tests/test_determinism_regression.py`: calls each of the 12 numeric
  layers twice with an identical body and asserts byte-identical JSON — enforcing
  §34's core reproducibility claim on the live HTTP surface (not just via
  `/reproduce`'s per-run hash). Catches unseeded RNGs, dict/set iteration-order
  leakage, wall-clock bleed, float reduction-order drift. Plus a seeded
  Monte-Carlo check: `/uncertainty` must be exactly reproducible for a fixed seed.
  LLM-prose layers excluded (their prose is Generated by design).
- Empirically verified all 12 stable before locking it in. Test-track only; no
  `backend/app/**` behaviour changed. `pytest` **234 passed** (+2); boots, 33 routes.

## 2026-08-13 — Verification run (roadmap complete)
- ROADMAP_ENGINE.md fully checked: 28/28 items done (M3–M7 + Stretch + Extended
  SPEC coverage + Hardening). No unchecked items remain.
- Health check: `pytest` **234 passed** in ~47s; `app.main:app` boots with **33
  routes** (28 functional endpoints + docs/openapi/redoc/health). Working tree clean
  before this entry.
- SPEC §34 guardrails intact and enforced by the integration smoke + determinism
  regression guards (no LLM in the numeric path; provenance tags present; SIMULATED
  media banner; widening uncertainty; byte-reproducible core).
- No new numeric behaviour changed this run — engine surface stable and demo-ready.

## 2026-08-13 (11:34 UTC) — Verification run (roadmap complete, re-checked post-UI pushes)
- `git pull --rebase --autostash`: already up to date. ROADMAP_ENGINE.md still
  28/28 checked — no unchecked engine items remain.
- Health check: `pytest backend/tests` **234 passed** (~51s); `app.main:app` boots
  with **33 routes** (28 functional endpoints + docs/openapi/redoc/health).
- SPEC §34 guardrails verified intact by the standing guards (integration smoke +
  determinism regression): no LLM in the numeric path, provenance tags present,
  SIMULATED media banner, widening uncertainty, byte-reproducible core.
- No `backend/app/**` behaviour changed this run — engine surface stable, demo-ready.

## 2026-08-13 (engine run — new hardening guard: uncertainty widens with horizon)
- Roadmap was fully checked off (28 items + stretch/extended/hardening). Verified green
  first: **234 tests passing**, app boots with **33 routes**. Rather than a third identical
  verification commit, added a genuinely new hardening guard that closes a real gap.
- **Gap closed:** SPEC §34 makes three numeric-core promises. Two were guarded globally
  (determinism regression → *reproducible*; integration smoke → *tagged + LLM-free*), but
  the third — *uncertainty widens with the horizon* — was only tested per-layer (timeline,
  ensemble). Nothing guarded it across the forecast surface the UI actually plots, so a
  refactor that flattened one band-series would slip through every existing test.
- **Added `backend/tests/test_uncertainty_widening_guard.py`** (test-track only, zero
  `backend/app/**` change). Recursively finds every band-series (t_months/low/high points)
  in `/simulate` **and** `/simulate/amend` — including nested world_a / world_b / delta /
  amended — and asserts: (1) band width is monotonically non-decreasing with horizon;
  (2) the far horizon is *strictly* wider than T0 for every base-forecast series, so a
  degenerate flat band also fails (the fan chart must actually fan out); (3)
  low ≤ value ≤ high everywhere. Mutation-tested: a hand-crafted narrowing band trips the
  guard, confirming it is not a no-op.
- **237 green** (was 234), app boots with **33 routes**. Demo credibility claim now has all
  three §34 invariants under a standing test.

## 2026-08-13 (engine run — new hardening guard: cross-layer mode-choice consistency)
- Roadmap fully checked off (28 items + stretch/extended/hardening). Verified green first:
  **237 tests passing**, app boots with **33 routes**. Rather than a fourth identical
  verification commit, added a genuinely new hardening guard closing a real gap.
- **Gap closed:** the spatial (§7.7) and microsim (§7.3) layers both claim to read the *same*
  deterministic mode-choice model as `/simulate` — spatial via `choose_mode`/`choose_mode_policy`,
  microsim via `mode_options`/`policy_mode_options`+`pick_mode`. Nothing enforced that these paths
  actually agree with the canonical `/simulate` split. Per-layer tests check each layer in
  isolation, so a refactor to `choose_mode` (that the `mode_options` path no longer mirrors), or a
  layer sampling a different population, would silently build a road network / who-gains-who-loses
  table on a *different* mode split than the headline numbers — the exact §34-forbidden cross-layer
  contract drift the determinism/tag/widening guards don't catch (they check reproducibility,
  provenance tags, and fan-out — not cross-layer numeric agreement).
- **Added `backend/tests/test_cross_layer_consistency.py`** (test-track only, zero `backend/app/**`
  change). Computes the canonical World-A/World-B car-commuter set from the population once, then
  over **four structurally-distinct policies** (reinvesting charge, general-fund charge,
  pedestrianisation, behavioural no-op) asserts: (1) `/simulate` reports the exact canonical car
  counts; (2) the microsim primitives reproduce `choose_mode`/`choose_mode_policy` **agent-by-agent**;
  (3) `_car_demand` loads exactly the canonical car set (peak trips = canonical × rep-factor ×
  peak-share; mutation-checked that a one-driver drift trips it); (4) a no-op is identical across
  layers; (5) all layers partition the one synthetic population.
- **251 green** (was 237), app boots with **33 routes**. The "one source of truth for the mode
  split" claim that lets spatial + microsim sit next to the ABM is now under a standing test.

## 2026-08-13 (engine run — new §34 guard: rogue-LLM numeric-invariance)
- Roadmap fully checked off (30/30). Verified green first: **251 tests passing**, app boots
  with **33 routes**. Rather than a fourth identical verification commit, closed a real §34 gap.
- **Gap closed:** SPEC §34 guardrail #1 — *LLMs never generate core numeric effects* — was only
  ever exercised through the **no-key fallback path**. Every existing parliament/press test runs
  with no LLM configured, so the entire LLM-**enabled** code path was untested: nothing proved
  that a model that *is* wired in can't leak numbers into a response. A refactor that parsed
  figures back out of prose, let the model rewrite an evidence point / cited ref, or recomputed a
  tally from generated text would pass every current test.
- **Added `backend/tests/test_llm_numeric_invariance.py`** (test-track only, zero `backend/app/**`
  change). For each prose surface it runs the pipeline twice — honest template path vs. the LLM
  seam monkeypatched to a **hostile model** that discards the evidence and emits fabricated
  figures (`999%`, `42 trillion`, `7 personas`) — then asserts the two responses are byte-identical
  after stripping only the free-text prose leaves (`speech`, `opening_statement`, the inner
  `answer` string) and the legitimately-flipping `method` flag. A companion assertion proves the
  rogue prose *did* change the raw output, so the guard can never pass vacuously; extra checks
  confirm no fabricated figure reaches any `points` / `cited_refs` / `tally` / `public_mood` field.
  Third test pins the skeleton-extractor itself (drops prose leaf, keeps `stance`/`cited_refs`).
- Covers both `run_debate` (parliament, gated on `settings.llm_enabled`) and `run_press_conference`
  (press, gated on the `use_llm` param) — the two surfaces where LLM prose meets Simulated numbers.
- **254 green** (was 251), app boots with **33 routes**. "The model writes words, never numbers"
  is now enforced against an adversarial model, not just asserted in a docstring.

## 2026-08-13 (12:06 UTC engine run — new layer: Historical Analogue / Causal, SPEC §7.1)
Roadmap was fully checked (30/30) and green (254 tests) at run start; verified, then added the one
genuine remaining SPEC-layer gap. **SPEC §7.1 (Historical Analogue / Causal Layer)** existed only as
a thin saturating transfer function *inside* `app/ensemble/model.py` — no case database, no per-scheme
difference-in-differences, no transferability scoring, no endpoint. Now a first-class layer.

- `backend/app/analogues/` (`cases.py`, `schema.py`, `model.py`) + `POST /analogues` and
  `GET /analogues/cases`.
- Curated 8-scheme database (London CCZ, Stockholm, Singapore ALS/ERP, Milan Area C, Gothenburg,
  Oslo toll ring, Ghent circulation plan, Madrid Central LEZ). Each is an **illustrative/approximate
  published** figure — tagged Observed but every card flags `source_note` "not a live data source"
  (honest, SPEC §34). No LLM produced any figure; they are fixed auditable constants.
- Per case: **difference-in-differences** effect = treated change − background/control trend (strips the
  city-wide trend the scheme didn't cause). **Transferability** score from auditable factors (intervention
  family exact/cross-pricing, coarse none/low/mod/high charge strength, revenue-recycling match, documented
  city-context similarity) with published weights. Applicable cases pooled by `identification × transfer`
  into a central estimate + a **CI that widens** when evidence is weak/analogues disagree. Emits the exact
  §7.1 shape: estimated effect, CI, analogue quality, identification/parallel-trend diagnostics,
  transferability score.
- Behaviour: car ban pools only Ghent; a transit-only policy honestly reports **no comparable scheme**
  (estimate 0, diagnostic) rather than inventing one; general-fund vs reinvest charge differ via the
  revenue-recycling transfer factor.
- **SPEC §8 honesty cross-check** (optional, on by default): on the demo £12 charge the real analogues pool
  to ≈ **−21%** but the agent-based model predicts ≈ **−93%** → flagged **"large gap"** ("real flat cordons
  rarely exceed ~30%; lean on the analogue range as an empirical sanity floor"). Turns the ABM's cordon
  collapse into an explicitly-uncertain claim instead of false precision — a strong demo beat.
- Per-case outcomes Observed, transferred estimate Estimated; deterministic, no LLM (SPEC §7.1/§8/§34).
  Registered in the §33 model registry (`historical_analogue`, `llm_touches_numbers=False`) → **14 layers**.
- Honest `not_modelled`: illustrative headline effects not this city's microdata; single flat cordon
  headline (no per-corridor/distributional transfer — those are the spatial/microsim layers); transfer
  assumes similar behavioural response; coarse charge bucket, not PPP-adjusted.
- 12 tests; **266 green** (was 254), app boots with **35 routes** (was 33).

## 2026-08-13 — Time-Series Layer (SPEC §7.2) [NEW LAYER]

Engine roadmap was 100% checked (31/31). Rather than invent marginal features, closed the one
**genuine remaining SPEC §7 gap**: of the seven enumerated hybrid-forecast sub-layers, §7.1/§7.3/§7.4/
§7.5/§7.6/§7.7 all shipped as first-class layers, but **§7.2 (Time-Series Layer)** had no dedicated
implementation — it lived only implicitly as the reduced-form elasticity method *inside* the ensemble,
and `app/baseline/timeseries.py` is just a fixed-growth projection with a hand-set band, not a fitted
statistical model. §7.2 asks specifically for the layer that treats variables whose temporal structure
is informative and says: "Forecast World A first. Then policy models alter the baseline trajectory."

- `backend/app/timeseries/` (`params.py`, `history.py`, `schema.py`, `model.py`) + `backend/app/routers/
  timeseries.py` → `POST /timeseries`.
- **Synthetic history** (`history.py`): seeded monthly DGP per metric — trend + annual seasonality +
  AR(1) noise — **anchored** so the final month equals the deterministic ABM baseline snapshot value.
  The anchor keeps §7.2 continuous with `/simulate` (cross-layer consistency, SPEC §34); the path is
  honestly labelled **Simulated** synthetic history, not real observations (the synthetic city keeps no
  real logs). Damped trend/seasonality/noise for %-share metrics.
- **Structural fit** (`model.py`): OLS local-linear-trend + 12-month seasonal dummies, AR(1) on the
  residuals. **Forecasts World A first** across the Time-Machine checkpoints. Prediction-interval
  variance is **derived from the fit** — regression mean-estimation variance (`σ²·x₀ᵀ(XᵀX)⁻¹x₀`, grows
  with the extrapolation distance) + accumulated AR(1) innovation variance (`σ_e²(1−φ^{2h})/(1−φ²)`) —
  so the band **widens with horizon** honestly (SPEC §34) instead of by a pasted-on assumption. Reports
  in-sample MAPE **and** an honest out-of-sample backtest (refit on all but a held-out 12-month tail →
  forecast MAPE).
- **Policy step**: the deterministic ABM Δ(B−A) shifts the fitted World-A trajectory to World B —
  multiplicative for volumes, additive %-points for shares. "Policy models alter the baseline
  trajectory" (§7.2 verbatim). Demo £12 reinvest charge: World-A cordon drifts ~3.3–3.7k/day with a
  fan-out band (95% width 142→425 trips over 10 yr, monotone), World B ≈ −92% post-T0 (tracks the ABM);
  a zero-charge no-op leaves World B ≡ World A; share shift additive, 0 at T0.
- Provenance: synthetic history **Simulated**, statistical baseline forecast **Estimated**, policy shift
  **Simulated**. Deterministic, no LLM in any number (SPEC §7.2/§8/§34). Registered in the §33 registry
  (`time_series`, `llm_touches_numbers=False`, assumptions read live from `DEFAULT_TS_PARAMS`) → **15
  layers**. Added to the integration-smoke + determinism-regression standing guards.
- Honest `not_modelled`: synthetic (not measured) history; univariate per metric (no VAR / exogenous
  regressors beyond trend/seasonality); Gaussian intervals (not a full Bayesian posterior / bootstrap);
  the behavioural response is the ABM's — the TS layer only shapes the baseline trajectory + uncertainty.
- 9 tests; **275 green** (was 266), app boots with **36 routes** (was 35).

## 2026-08-13 — Data Fabric: dataset ingestion & provenance layer (SPEC §4) [NEW LAYER]

Engine roadmap was 100% checked. Rather than invent a marginal feature, closed a genuine
remaining SPEC gap: **§4 (Data Fabric — ingestion & provenance layer)** was one of the few
enumerated top-of-pipeline SPEC sections with no first-class endpoint. `/evidence` (§26) traces a
single *metric*, `/registry` (§33) catalogues the *models*, `/reproduce` (§32) pins dataset byte
hashes for one run — but nothing published the dataset-level catalogue with the full §4 provenance
record + harmonisation lineage the spec mandates.

- `backend/app/datafabric/` (`schema.py`, `model.py`, `__init__.py`) + `backend/app/routers/
  datafabric.py` → `GET /data-fabric`. Wired in `main.py` (37 routes now, was 36).
- **Full §4 metadata schema per dataset, built live from disk**: title / publisher / source_url /
  retrieved_at / geographic_scope / spatial_resolution / time_start-end / frequency / units /
  variables / license / missingness / revision / confidence / transformation_history. Record counts,
  per-variable dtype+unit+description, **measured missingness** (scans real records — 0% on the
  complete synthetic files, reported not assumed) and a content-addressed **`revision` = sha256 of
  the actual file bytes** are all computed on disk at request time, so the catalogue cannot drift
  from what the engine reads. Shared scope/licence read from `manifest.json`.
- **Dataset cards**: zones / roads / od_pairs / population / buildings — each **Simulated**, publisher
  = the synthetic generator, with real datasets (ONS WU03EW, 3DCityDB, Census microdata, OSM, LODES,
  WebTAG) listed only as **schema analogues**, never as live sources (SPEC §34 honesty). Plus the
  mode-choice **assumption-set** card (Estimated, variables introspected live from `DEFAULT_PARAMS`).
- **§4 supported-format contract** with honest wiring status: JSON + GeoJSON `native`; CSV/XLSX
  `adapter-ready`; GTFS / gov-APIs / census / budget / Hansard / election / consultation / survey /
  environmental / admin `declared` (part of the ingestion contract, not exercised in the synthetic
  demo).
- **§4 harmonisation pipeline**, honest about what actually runs: geographic joins (all layers key on
  `zone_id`), schema mapping (`dataset.py` typed accessors), unit normalisation (money↔minutes, km/h,
  veh/hr), population weighting (sample→city rep-factor), provenance tracking (byte hashes +
  MetricTags), dedup, missing-data treatment → *implemented* with the code path; time alignment /
  inflation adjustment / outlier detection → **N/A** for a single-snapshot synthetic city, with the
  reason, rather than faking precision. Emits the mandated `input data → transformation → model →
  assumptions → result` lineage contract.
- Provenance: the fabric is **Observed** about the data itself (transparency artifact, not a
  forecast). Fully deterministic, no LLM (SPEC §4/§34). §33 registry left untouched — the fabric is
  data-side, the registry model-side; kept separate like §32/§26. Added `/data-fabric` to the
  integration-smoke GET sweep.
- Honest scope: no real feed is ingested (synthetic city), so the fabric documents the ingestion +
  harmonisation *contract* a real deployment would exercise, and measures/labels the synthetic files
  truthfully rather than dressing them up as observations.
- 9 tests; **284 green** (was 275), app boots with **37 routes** (was 36).
- 2026-08-13 — Scenario orchestrator `POST /run` (SPEC §28/§29): the composition endpoint the
  killer demo is a script for. New `backend/app/scenario/` (`schema.py` + `service.py`) +
  `backend/app/routers/run.py` compose the full §29 narrative in ONE call — compile (NL→DSL or
  accept a pre-compiled `policy`) → `/simulate` A/B/Δ+ledger → `/public` reaction → `/parliament`
  debate → an auto-derived amendment re-simulation (`compare_amendment`) → `/media` feed — in one
  mutually-consistent envelope. NO new numeric model: reuses the exact endpoint services, so the
  composed numbers are byte-identical to the standalone endpoints (tests pin `headline == /simulate
  delta @ horizon` and `net_support == /public`). Auto-amendment mirrors the §29 beat: flat charge
  w/o income exemption → exempt low-income (`auto:equity`); already-equitable+full-reinvest → none;
  caller can override (`source:'caller'`). Returns a 6-beat timecoded §29 narrative + a headline
  dashboard (cordon traffic / CO₂ / car share / transit ridership / peak crowding at the horizon,
  default Year 2) with direction + Δ band. Numbers Simulated, prose Generated, no LLM in any figure;
  numeric sections deterministic (byte-identical across two runs); 422 when neither text nor policy
  given. Added `/run` to the integration-smoke sweep. `test_scenario_run.py` (10 tests). 294 green;
  app boots with 38 routes.
