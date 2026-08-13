# PROGRESS — UI track (frontend)

Dated notes, newest at the bottom. One line per shipped item.

- 2026-08-13 — M4.1: Installed MapLibre GL + deck.gl (+ react-map-gl). Rendered the
  Meridia 3D world: extruded zone choropleth (Residents/Jobs/Job-density switcher),
  road network with cordon-crossing links highlighted, and the CBD cordon polygon.
  Tile-free MapLibre base (no API key, offline), deck.gl overlay via MapboxOverlay,
  hover tooltips, legend, and a "Synthetic" provenance stamp. Geometry bundled to
  `frontend/public/city/` from `data/city/` (loader prefers `NEXT_PUBLIC_CITY_BASE_URL`
  if the backend later serves `/city`). `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M4.2: Added switchable deck.gl overlays — Traffic flow, Transit demand,
  Support/opposition. Transit heatmap is derived from the real synthetic OD matrix
  (tagged Synthetic, world input); traffic (corridor-load index from link capacity)
  and support (distance-from-CBD gradient) are clearly stamped Placeholder until
  `/simulate` is live (SPEC §34). Each overlay shows a provenance chip + honesty
  caption + legend. Pure metadata split into overlayMeta.ts to keep the WebGL stack
  out of SSR. OD matrix lazy-loaded (~0.4 MB) only when transit is selected.
  `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M4.3: Added the Time Machine scrubber (draggable slider + clickable
  T0→10y ticks) inside a new TwinWorkspace parent that fetches `GET /baseline` and
  shares the selected-checkpoint state. Scrubbing drives the map's time badge (and
  the dashboard, next item). When the backend is down the map still renders and the
  timeline shows an honest "waiting for backend" state — no invented numbers
  (SPEC §34). `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M4.4: Outcomes dashboard — 5 tiles (Traffic, CO₂, Transit, Equity,
  Support). Traffic/CO₂/Transit read the World-A baseline series at the scrubbed
  checkpoint with an SVG sparkline showing the widening uncertainty band, ± band %,
  provenance chip, and a "vs T0" drift delta (direction-aware colouring). Equity &
  Support have no baseline series → explicit "awaiting /simulate" placeholders;
  "vs baseline" delta reads "simulate a policy" until World B exists (SPEC §34).
  **M4 complete.** `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M5.1: Model Parliament view. Added a shared TwinStore context (compiled
  policy + active simulation) so the compiler publishes the DSL and downstream panels
  consume it. ParliamentPanel convenes `POST /parliament/debate` and renders the motion,
  stance tally, and each persona's argument (headline, speech, points, confidence bar)
  with evidence-citation chips (metric/event + provenance) and the synthesis. Prose is
  labelled Generated, cited figures Simulated (SPEC §34). Typed clients for /simulate,
  /parliament/debate, /parliament/failure-modes + a client-side applyAmendment mirror
  of the backend added to lib/api.ts. Backend contracts matched against source; graceful
  states when it's down. `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M5.2: Apply-amendment + re-simulate loop (the killer interaction,
  SPEC §29). Added a "Simulate policy" button to the Time Machine bar and an
  Amendment queue in the Parliament panel (exempt low-income / exempt residents /
  raise charge ×1.5 / reinvest 90% in transit). Each applies a structured DSL edit
  (client mirror of the backend `apply_amendment`) then re-runs `POST /simulate`,
  writing World A/B/Δ into the shared TwinStore. The outcomes dashboard flips from
  World-A baseline to World B + the real Δ(B−A) per tile (value, %, effect
  sparkline with widening band), tags everything Simulated, and shows an "Amended"
  banner naming the active amendment; the map time badge switches to "World B".
  "Show baseline" reverts. Every number comes from the model — no fabricated
  effects (SPEC §34). `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M5.3: Failure Mode Register (Devil's Advocate "Red Team" panel,
  SPEC §12/§27). New FailureModesPanel convenes `POST /parliament/failure-modes`
  on the compiled policy and renders the ranked register: each mode shows a
  severity chip (low→critical), an estimated-likelihood meter, the composite risk
  score (severity weight × probability, the ranking key), the causal mechanism, a
  concrete mitigation callout, modelled exposure (commuters/trips), and the
  Simulated evidence chips it rests on. Provenance stated honestly — risk scores
  Estimated, cited figures Simulated; an empty register renders an explicit
  "no modes raised" state rather than inventing risk (SPEC §34). Graceful
  no-policy / loading / error states. **M5 complete.** `tsc --noEmit` +
  `next build` clean.
- 2026-08-13 — M6.1: Public reaction view (SPEC §13/§27). New PublicReactionPanel
  convenes `POST /public` and renders the cohort opinion distribution as diverging
  Likert bars — an overall bar (net-support chip + population) plus a switchable
  breakdown by Income band / Geography / Travel mode, size-weighted client-side
  from the cohort list and ordered (income low→high, else by net support). Follows
  the dataviz conventions: opinion is a polarity scale → a diverging green(support)
  ↔ red(oppose) ramp with a gray neutral midpoint and muted "uncertain", poles
  dark / mid-arms light, 2px surface gaps between segments, direct % labels + a
  shared legend + per-segment hover tooltips as secondary encoding (never colour
  alone). Every fraction tagged Simulated — a deterministic structural model, not
  a poll (SPEC §34). Graceful no-policy / loading / error states. `tsc --noEmit` +
  `next build` clean.
- 2026-08-13 — M6.2: Simulated press feed (SPEC §15/§27). New PressFeedPanel
  convenes `POST /media` and renders archetype coverage grouped by horizon
  (Month 5 / Year 2). Each card shows the fictional generic outlet, its archetype
  (public broadcaster / business press / local / tabloid / environmental /
  industry), the headline + standfirst, a sentiment chip, the archetype's angle,
  and the event-ledger/metric refs it was "built from". Guardrail (SPEC §15/§34):
  a persistent SIMULATED disclaimer banner up top plus a SIMULATED stamp on every
  card, tagged Generated; no real outlets/bylines and no invented figures — cards
  cite only model refs. Graceful no-policy / loading / error states. **M6
  complete.** `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M7.1: Evidence drawer (SPEC §26). Each dashboard tile with a metric
  key now shows an "Evidence ▸" button (wired only when a policy exists) that opens
  a slide-over drawer fetching `POST /evidence` for that metric at the scrubbed
  horizon. The drawer walks the causal trace: World A/B/Δ result cells + band, a
  horizon-aware confidence meter, the verbatim ascii_trace ladder, the chain nodes
  (input-data → transform → model → assumption → result, each tagged), the
  behavioural rules/equations (value, parameter, plausible range, sensitivity,
  source), the named assumptions, real-world analogues (Observed, flagged
  illustrative-only), and citations. Scrim + Escape/✕ to close; loading/error
  states. Every number is copied from the deterministic sim — no LLM on the
  numeric path (SPEC §34). Added tag colours for Observed/Estimated. `tsc --noEmit`
  + `next build` clean.
- 2026-08-13 — M7.2: Main-screen assembly per SPEC §27 + demo flow (SPEC §29).
  TwinWorkspace now lays the 3D world (left) beside the outcomes panel (right) in
  a responsive two-column grid that collapses to one column ≤1000px, with the
  draggable timeline + Run-counterfactual bar spanning full width below. New
  PanelTabs component renders the [Parliament] [Public] [Press] [Red Team] tab bar
  as the lower deck; all four panels stay mounted (toggled with `hidden`) so a
  debate/opinion/press/register survives tab switches during the demo. Wired the
  §29 verbs: the primary sim button reads "Run counterfactual" (then
  "Re-simulate policy"), so the 60-second script flows compile → run counterfactual
  → scrub → Parliament amendment + re-simulate → Press at Year 2. `tsc --noEmit`
  + `next build` clean.
- 2026-08-13 — M7.3: Visual polish + robustness. Rendered the app in headless
  Chrome at desktop (1440w) and mobile (390w) and eyeballed it: the SPEC §27
  two-column top (3D world + outcomes) collapses cleanly to one column, cards and
  segmented controls wrap, the tab bar wraps, and the honest loading/waiting/empty
  states all render (no invented numbers with the backend down). Hardened
  `getHealth`: a foreign service answering 200 on the same host/port used to read
  as a healthy URBAN backend with blank fields — now the client validates the
  /health shape and surfaces a clear "another service on this port?" error instead
  (SPEC §34 honesty). Added a ≤460px fallback so the evidence drawer's World A/B/Δ
  result grid stacks to one column on narrow screens. **M7 complete — ROADMAP_UI
  fully checked off.** `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M8.1: SDG alignment tab (SPEC §23). New SdgPanel convenes `POST /sdg`
  on the compiled policy and renders the alignment report grouped by goal (SDG 11/16
  core, 10/13 secondary). Each goal lists its measurable indicators / transparent
  proxies with baseline vs scenario, a direction-aware change (toward/away from the
  target, coloured by whether it improves — not merely by sign), a confidence chip
  (high/med/low + %), the data source, and the provenance tag. The headline is a
  count of improved/worsened/unchanged indicators at the horizon — **no composite
  "SDG score"** (SPEC §23 forbids one). Everything tagged Simulated; graceful
  no-policy/loading/error states, no invented alignment when the backend is down
  (SPEC §34). Typed `runSdg` client + SDG types added to lib/api.ts. `tsc --noEmit`
  + `next build` clean.
- 2026-08-13 — M8.2: Opinion-diffusion tab (SPEC §14). New DiffusionPanel convenes
  `POST /diffusion` and visualises the Friedkin–Johnsen run: a multi-line SVG
  chart of every actor's opinion trajectory over the information rounds on the
  full bipolar [-1,+1] scale, with a solid zero midline, ±1 gridlines, citizen
  cohorts drawn heavier than institutional actors, and information-shock markers.
  Trajectories are coloured on the dataviz diverging polarity ramp by final
  stance (green support / red oppose / slate contested) with a legend + hover
  titles so colour is never the only channel. Adds a citizen net-support swing
  (round 0 → final), the dominant narrative, salience + polarisation mini-lines,
  and a ranked coalition list (stance, citizen share bar, mean opinion, members).
  Honesty (SPEC §14/§34): the header states rounds are information steps, NOT the
  Time-Machine horizon; everything tagged Simulated; graceful
  no-policy/loading/error states. Typed `runDiffusion` client + diffusion types
  added to lib/api.ts. `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M8.3: Backtest scorecard tab (SPEC §25). New BacktestPanel is
  policy-independent: it loads the engine's built-in benchmark case via
  `GET /backtest/example` (showing its name/description) and scores the forecast
  with `POST /backtest`. Renders the scorecard as stat tiles — MAE, RMSE, MAPE,
  direction accuracy, interval coverage (calibration), mean event-timing error —
  plus a per-metric forecast-vs-actual table (forecast, actual, error, direction
  ✓/✗, in-band ✓/✗). Honesty (SPEC §25/§34): the forecast is stamped Simulated,
  and because the built-in case's *actuals* are a synthetic benchmark (not real
  observations) that provenance is stamped prominently on the case card AND a
  dashed banner over the scores, so a good score is never mistaken for real-world
  validation. Typed `getBacktestExample`/`runBacktest` clients + backtest types
  added to lib/api.ts. Tabbar hint notes Backtest runs without a compiled policy.
  **M8 complete.** `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M9.1: Ensemble forecast tab (SPEC §8). New EnsemblePanel convenes
  `POST /ensemble` on the compiled policy and shows the flagship cordon effect as
  estimated by three independent methods (structural agent-based, historical-
  analogue transfer, reduced-form elasticity). The headline is the pooled central
  estimate with an explicit band that spans *method disagreement* — a disagreement
  chip (methods agree / some disagreement / methods disagree, coloured green/amber/
  red) plus the raw spread in points makes clear a wide band means the methods
  diverge, NOT false precision (SPEC §8). A shared-scale range chart draws each
  method's own low…high range + central marker, staggered, with the pooled
  ensemble band as a highlighted vertical span and a zero line; inapplicable
  methods (weight→0) are greyed, not dropped, with an explicit note. A method
  detail grid lists each method's central/range, ensemble weight, SPEC §7 layer,
  approach, and provenance tag. Everything tagged Estimated (a cross-method blend,
  not one Simulated run); no LLM on the numeric path (SPEC §34); graceful
  no-policy/loading/error states, no invented forecast when the backend is down.
  Typed `runEnsemble` client + Ensemble/Method types added to lib/api.ts, wired as
  a new "Ensemble" tab in PanelTabs. `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M9.2: Model registry / transparency tab (SPEC §33). New
  RegistryPanel loads `GET /registry` on mount (policy-independent — it describes
  the engine, not a run) and renders the transparency manifest that answers "how
  do we know these numbers aren't AI astrology?". Headline artifact is the SPEC
  §34 guardrail checklist: each rule shown with a ✓/✗ pass mark (green/red left
  border), the rule text, and how the codebase concretely enforces it, plus an
  all-N-enforced summary chip. Below: summary count tiles; model cards for every
  forecast layer (SPEC sections, determinism badge det/stoch, layer, output tag,
  method, inputs/outputs, live assumption chips, code path) — each carrying the
  key honesty badge "numbers: model only" vs a red "⚠ LLM touches numbers" driven
  by produces_numbers/llm_touches_numbers, plus the LLM's prose-only role; data
  source cards (kind/tag/used-by); and a collapsible assumption index table of
  every live-introspected value + source + tag. The manifest is tagged Observed
  (describes code). Honest backend-down state with a Retry — never pretends the
  guardrails hold when it can't load them. Typed `getRegistry` client + registry
  types added to lib/api.ts; wired as a new "Registry" tab (tabbar hint notes it
  runs without a compiled policy). `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M9.3: Institutional review tab (SPEC §18). New InstitutionsPanel
  convenes `POST /institutions/review` on the compiled policy and renders the
  four institutional agents (Climate, Implementation, Legal/Constitutional,
  Auditor). An overall banner shows the single most-severe verdict (deterministic,
  not averaged) with a per-verdict tally and the cross-agent synthesis. Each agent
  card carries its mandate, a colour-coded verdict badge (clear/conditional/
  concern/block → green/amber/orange/red left border), confidence, a one-line
  summary, a severity-tagged findings list (info/watch/risk/blocker), a concrete
  recommendation, and evidence citations that point at the model's metric/event
  refs — each stamped with its provenance tag. Honesty (SPEC §18/§34): the header
  and the response tag make clear the review prose is Generated while every cited
  number is Simulated from the model; no LLM produces a figure. Graceful
  no-policy/loading/error states; no invented verdicts when the backend is down.
  Note the endpoint is `/institutions/review` (not `/institutions`). Typed
  `runInstitutions` client + institution types added to lib/api.ts (reusing the
  existing EvidenceCitation type); wired as a new "Institutions" tab. **M9 complete.**
  `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M10.1: Press conference tab (SPEC §16). New PressConferencePanel
  stages `POST /press-conference` on the compiled policy: a spokesperson opening
  statement plus five archetype journalist exchanges (public broadcaster, business
  press, tabloid, environmental, opposition-local). Each question shows the
  fictional outlet + reporter, an archetype chip, a hostility chip (friendly/
  neutral/hostile, green→red), the line of attack, and the model refs it's
  grounded in; each answer shows the spokesperson's stance (defends/acknowledges/
  rebuts/commits, colour-coded) and its own grounding refs. A dashed SIMULATED
  disclaimer banner sits at the top, the run is stamped SIMULATED, and the
  header surfaces the horizon, room mood and whether the prose was LLM-polished or
  templated. Honesty (SPEC §16/§34): fictional outlets/reporters only, prose
  Generated over Simulated figures, every Q&A anchored to a metric/event ref, no
  LLM-invented numbers; graceful no-policy/loading/error states. Typed
  `runPressConference` client + press types added to lib/api.ts; wired as a new
  "Presser" tab (distinct from the /media-driven "Press" headline feed).
  `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M10.2: Counterfactual compare tab (SPEC §21). New ComparePanel
  convenes `POST /compare` on the compiled policy and renders World A (baseline)
  vs World B (intervention) vs any amendment worlds C/D…. The user toggles a small
  set of structured preset amendments (exempt low-income, exempt residents, +50%
  charge) to spin up extra worlds — transparent structured edits, not free text.
  Output: a world legend (A baseline always shown per SPEC §21, B intervention,
  amendment worlds with their edit counts, colour-coded by role) and a horizontally
  scrollable headline table — one row per metric, columns = baseline value + each
  world's value with its Δ-vs-baseline (absolute + %, direction arrow, neutral
  up/down colouring that does NOT imply good/bad since metric direction varies).
  Honesty (SPEC §21/§34): baseline never omitted, every number Simulated, Δ =
  world − baseline. Graceful no-policy/loading/error states. Typed `runCompare`
  client + comparison types added to lib/api.ts (reusing the Amendment type);
  wired as a new "Compare" tab. `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M10.3: Uncertainty fan tab (SPEC §24). New UncertaintyPanel
  convenes `POST /uncertainty` for a chosen metric of the compiled policy and
  renders the Monte-Carlo fan of futures. Centerpiece is an SVG fan chart: nested
  50/80/95% interval bands (light→dark) with a median trajectory line across every
  Time-Machine checkpoint, a dashed zero line and y/x axis labels — uncertainty
  made visible, not a false-precision point. Alongside: the headline median Δ with
  its three intervals and the deterministic point estimate + sample count/seed
  (reproducible); a sensitivity tornado ranking the most-influential assumptions
  by their one-at-a-time swing (bars centred on zero, low→high span); and the
  behavioural-regime disagreement ensemble (per-regime Δ + spread). Metric key is
  a text input defaulting to traffic.daily_vehicle_km; on an unknown key the
  backend's 404 returns the valid keys, surfaced as one-click chips (typed
  MetricNotFoundError) rather than guessing. Honesty (SPEC §24/§34): every number
  is a re-run of the deterministic model with perturbed assumptions, tagged
  Simulated, no LLM on the numeric path. Typed `runUncertainty` client +
  uncertainty types added to lib/api.ts; wired as a new "Uncertainty" tab.
  `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M10.4: Policy optimiser tab (SPEC §22). New OptimiserPanel is
  policy-independent: it works the problem backwards via `POST /optimise` — the
  user optionally sets constraint knobs (max commute +%, max low-income burden +%,
  max budget $M), the backend grid-searches candidate interventions, simulates
  each, and returns the feasible Pareto frontier. Renders: a feasibility banner
  (n_feasible/n_candidates, frontier size, green/red on constraints_satisfiable);
  four representative recommendation cards (cheapest / most equitable / largest
  CO₂ cut / best balanced) resolved from policy_id to the candidate's label +
  headline metrics; and a horizontally scrollable Pareto-frontier table (emissions
  ↓, traffic ↓, commute ↑, low-income ↑, net support, cost) per candidate.
  Honesty (SPEC §22/§34): outcome metrics tagged Simulated; the est_cost column is
  explicitly flagged as an Estimated documented budget proxy (starred, with an
  Estimated tag note), never a simulated outcome and never LLM-produced. Graceful
  idle/loading/error states. Typed `runOptimise` client + optimiser types added to
  lib/api.ts; wired as a new "Optimiser" tab (tabbar hint notes it runs without a
  compiled policy). **M10 complete — every documented engine endpoint now has a UI
  surface.** `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M11.1: Guided demo tour (SPEC §29). With every documented engine
  endpoint now surfaced, added a presentation layer that walks a judge through the
  60-second flow. New `lib/demo.ts` holds the ordered TOUR_STEPS (draft → compile →
  run counterfactual → scrub the Time Machine → read the tagged outcome tiles →
  Parliament debate + amendment re-sim → Red Team failure register → transparency
  Registry) plus a tiny pub/sub (`subscribeDemoTab`/`requestDemoTab`) so a step can
  switch the analysis tab bar without lifting PanelTabs' local state into a global
  store. New `DemoTour` component renders a fixed "▶ Guided demo" launcher and, once
  open, a spotlight overlay: it scrolls each step's `data-tour` anchor into view,
  punches a lit hole around it via a huge box-shadow dimmer, and shows a caption
  card with Back/Next/Done, a step counter, ✕/Esc close and ←/→ keyboard nav; the
  spotlight re-measures on scroll/resize so it stays glued to its anchor. Added
  stable `data-tour` anchors to the compiler, 3D map, outcomes dashboard (both the
  ready and waiting-for-backend states), timeline card and the tab bar; PanelTabs
  subscribes to demo tab requests. Honesty (SPEC §34): the tour is pure guidance —
  it never renders or invents a metric, it only points at what the backend produced
  (or its "waiting for backend" state) and narrates the flow. `tsc --noEmit` +
  `next build` clean.
- 2026-08-13 — M12.1: Demo resilience — App Router error boundaries (SPEC §34).
  With every documented engine endpoint surfaced and each panel already handling
  its own fetch idle/loading/error states, the remaining gap was a *render* throw:
  an unexpected backend payload shape, a deck.gl/MapLibre runtime error, or a deep
  null deref inside a chart is not caught by a panel's try/catch and would blank the
  whole app to Next's default crash page — reading, mid-demo, as "the product broke".
  Added `app/error.tsx` (segment boundary, renders inside the root layout so it reuses
  globals.css theme tokens + .card/.btn/.eyebrow utilities; logs to console; offers
  Try again = reset() and Reload = location.reload) and `app/global-error.tsx` (root
  boundary for a layout-level throw — it replaces the whole document, so it renders its
  own <html>/<body> with self-contained inline styles matching the brand palette and a
  reset() reload). Both keep the honesty contract: a clear failure message + the error
  digest for debugging, and NEVER a fabricated or estimated number (SPEC §34). Added two
  small utility classes (.error-boundary, .error-actions) to globals.css. Verified full
  suite: `tsc --noEmit` clean, `next lint` clean (0 warnings), `next build` clean (4/4
  static pages). **M12 complete.**
- 2026-08-13 — M12.2: Themed 404 (`app/not-found.tsx`). Completes the error-surface
  coverage started by the boundaries: a bad URL now lands on an on-brand page (reuses
  globals.css theme + .btn primary) with a Link back to the twin, instead of Next's
  bare default 404 — off-brand mid-demo. Static, self-contained, no data or metrics.
  Build now emits a custom `/_not-found` route. `tsc --noEmit`, `next lint`, `next
  build` all clean. **M12 complete — the UI is crash-safe end to end.**
- 2026-08-13 — Verification run: whole UI roadmap (M4–M12) complete; confirmed
  `tsc --noEmit` clean, `next lint` clean (0 warnings), `next build` clean (4/4 static
  pages), and all 18 documented backend endpoints surfaced in the frontend (grep of
  `lib/api.ts` + panels: /health /baseline /policy/compile /simulate /parliament/debate
  /public /media /evidence /uncertainty /compare /optimise /backtest /sdg /diffusion
  /registry /press-conference /ensemble /institutions). No new backend endpoint to expose.
- 2026-08-13 — M13: Judge-facing frontend docs (SPEC §33/§34). The app is feature- and
  crash-complete; the remaining gap was legibility for a reviewer reading the *repo* (not
  the running app). Rewrote `frontend/README.md` from a bare run/config guide into a
  proper front-door: architecture overview (App Router pages, `lib/api.ts` typed client,
  map/twin component split, TwinStore state flow), the full analysis-tab → endpoint →
  SPEC-section map for all 18 endpoints, and a "Honesty contract in the UI" section that
  documents *how* SPEC §34 is actually enforced in code — the `MetricTag`
  Observed/Estimated/Simulated/Generated provenance chips (`.tag.*` classes), the
  never-fabricate-a-Δ placeholder behaviour in MetricTile, visible uncertainty bands
  (sparkline ±, Monte-Carlo 50/80/95%, ensemble disagreement), SIMULATED media stamps,
  "waiting for backend" states, and the crash-safe error boundaries. Every claim verified
  against the real code (MetricTag union in `lib/api.ts`, `.tag.observed/.estimated/`
  `.simulated/.generated/.synthetic` in `globals.css`, evidence is POST, compile is SPEC
  Step 2) — no fabricated numbers, docs only. Build/lint/typecheck unaffected (markdown).
  **UI track roadmap complete through M13.**
- 2026-08-13 — M14: Economy tab (`POST /economy`, SPEC §7.4). The engine track shipped
  the economic-spillover endpoint after the UI roadmap was declared complete; this run
  surfaces it. New `EconomyPanel` + `runEconomy`/`EconomicSpilloverReport`/`EconomicChannel`/
  `SectorExposure` types in `lib/api.ts`, wired as an "Economy" tab in `PanelTabs`. The panel
  renders the net partial-equilibrium annual impact with its low…high band + confidence +
  horizon; each transmission channel (mechanism, the **Simulated** physical driver it reads
  with its value, the **Estimated** banded monetary effect, direction glyph, confidence,
  elasticity/IO assumptions, note); per-sector exposure cards (direction + qualitative
  magnitude — deliberately NOT fabricated hard jobs numbers); the `not_modelled` honesty
  surface; and a collapsible auditable `assumptions` block. Honesty contract held: two
  provenance classes surfaced side by side (physical Simulated → money Estimated), band always
  visible, partial-equilibrium/no-CGE caveat prominent, `waiting`/`idle`/`error` states when the
  backend is down (never invents a figure). Added ~310 lines of scoped `.eco-*` CSS reusing the
  theme tokens + existing `.tag.*` chips. Updated `frontend/README.md` endpoint map (now 19
  surfaces). `tsc --noEmit` clean, `next lint` clean (0 warnings), `next build` clean (4/4
  static pages). **M14 complete — every documented backend endpoint incl. /economy is surfaced.**

- 2026-08-13 — **M15: Dynamics tab — POST /dynamics recursive feedback loop (SPEC §7.6/§19).**
  The engine track shipped `POST /dynamics` (the stocks-and-flows loop SPEC §19 calls "central
  to the concept") after M14 declared the UI roadmap complete; this run surfaces it. New
  `DynamicsPanel` + `runDynamics`/`SystemDynamicsResult`/`StockPoint`/`FeedbackEvent`/
  `FeedbackContrast` types in `lib/api.ts`, wired as a "Dynamics" tab in `PanelTabs`. The panel
  renders: the instantiated §19 cascade (`loop_description`); final-state tiles (charge in force,
  crowding demand/capacity, net support, amendments triggered); four pure-SVG banded stock charts
  over the 10-year horizon (transit demand vs capacity, crowding ratio with an over-capacity=1.0
  baseline, effective charge, net support with a neutral baseline) whose uncertainty band widens
  as per-checkpoint confidence falls (SPEC §9); a **political-response toggle** (endogenous-
  amendment arm ON/OFF); the closed-loop vs open-loop end-state `contrast` (the whole point of
  §19 — same deterministic model, only the amendment rule toggled) with signed deltas +
  interpretation; the second-order `feedback_events` with their ordered causal chains and
  month/year stamps; the `not_modelled` honesty surface; and two collapsible provenance blocks —
  **Simulated** structural anchors (from the ABM) and **Estimated** dynamics assumptions (the
  temporal coefficients). Honesty contract held: trajectory is deterministic/LLM-free → Simulated,
  couplings Estimated (both classes surfaced), bands always visible, `idle`/`loading`/`error`
  states when the backend is down (never invents a curve). Added ~360 lines of scoped `.dyn-*`
  CSS reusing the theme tokens + existing `.tag.*` chips. Updated `frontend/README.md` endpoint
  map (now 20 surfaces). `tsc --noEmit` clean, `next lint` clean (0 warnings), `next build` clean
  (4/4 static pages). **M15 complete — every documented backend endpoint incl. /dynamics is surfaced.**

- 2026-08-13 — **M16: Amendment effect surface — POST /simulate/amend (SPEC §12).**
  The engine exposes a dedicated `POST /simulate/amend` that re-simulates BOTH the
  original and amended policies over the same baseline and returns the isolated
  **Δ(amended − original)** — the amendment's own marginal effect. Until now the
  Parliament amendment loop only re-ran the amended World B through `/simulate` to drive
  the shared map/dashboard, so the chamber saw the amended-vs-baseline outcome but never
  what the amendment *itself* changed. This run surfaces it. Added `AmendmentComparison`
  type + `amendPolicy()` client in `lib/api.ts`, and extended `ParliamentPanel`'s
  "Apply + re-simulate" handler to fire `/simulate` (map drive) and `/simulate/amend`
  (isolated effect) together via `Promise.all` — both share the deterministic model so
  they stay consistent. New `AmendmentEffect` component renders the concrete structured
  `changes` as chips + an "Amendment effect vs original policy" table: per-metric signed
  Δ + % and the low…high band at the final checkpoint, with a near-zero row shown as
  "≈ 0 (no change)" so a barely-moving metric reads honestly rather than as noise. Clearly
  framed as distinct from the dashboard above (there the "before" is the baseline; here
  it's the *original policy*). Deterministic/LLM-free → stamped Simulated; honest error
  state when the backend is down (never invents a delta). Added ~120 lines of scoped
  `.amd-*` CSS reusing the theme tokens + existing `.tag.*` chips. Updated
  `frontend/README.md` endpoint map (now 21 surfaces incl. /simulate/amend). `tsc
  --noEmit` clean, `next lint` clean (0 warnings), `next build` clean (4/4 static pages).
  **M16 complete — the dedicated amendment-comparison endpoint is now surfaced.**

- 2026-08-13 — **M17: Distributional microsimulation surface — POST /microsim (SPEC §7.3).**
  The engine shipped `POST /microsim` (person-level "who gains, who loses, by how
  much") after M16 declared the UI roadmap complete; this run surfaces it. Added
  `GroupImpact` + `MicrosimReport` types and a `runMicrosim()` client to `lib/api.ts`
  (documented contract: `{ policy }` → per-agent distribution). New `MicrosimPanel`
  renders: a winners/losers/unaffected split with a share bar + population mean
  per-trip generalized-cost change + named biggest-winner / worst-hit groups; a
  prominent **charge-burden regressivity** card (ratio → verdict progressive/flat/
  regressive, payer count, mean payer burden %); and four breakdown tables — by
  income decile (with a burden-%-of-income column), household type, home
  neighbourhood, occupation — each row showing Δ generalized cost (scaled bar),
  daily money-equivalent, and the better/worse split. Honesty: welfare is
  deterministic/LLM-free → stamped Simulated, the money-equivalent uses a documented
  value-of-time → Estimated (both provenance classes shown); `not_modelled` list +
  auditable `params` surfaced; honest waiting/idle/error states — never invents a
  distribution when the backend is down (the current :8000 host is a different
  service, so the panel correctly stays in its pre-run state). Wired a new
  **Microsim** tab into `PanelTabs`; added ~230 lines of scoped `.ms-*` CSS reusing
  the theme tokens + existing `.eco-*`/`.tag.*` classes. Updated `frontend/README.md`
  endpoint map (now 22 surfaces incl. /microsim). `tsc --noEmit` clean, `next lint`
  clean (0 warnings), `next build` clean (4/4 static pages). **M17 complete.**

- 2026-08-13 — **M18: Spatial traffic-assignment surface — POST /spatial (SPEC §7.7).**
  The engine shipped `POST /spatial` (peak-hour static user-equilibrium assignment,
  MSA + BPR, over the real Meridia road grid; car demand = the driving subset of the
  same deterministic mode-choice agents as `/simulate`) after M17. This run surfaces
  it. Added `NetworkState` / `ArcLoad` / `ZoneChange` / `AccessibilityReport` /
  `PollutionReport` / `SpatialReport` types + a `runSpatial()` client to `lib/api.ts`.
  New `SpatialPanel` renders: a headline strip (peak-hour car trips A→B, cordon-inflow
  Δ%, network vehicle-hours Δ% with good/bad colouring); side-by-side World A
  (baseline) vs World B (policy) network-state cards (vehicle-hours/-km, mean speed,
  mean/max v/c, congested + overcapacity arc counts, cordon inflow); a notable-link-
  loads table (flow A→B with signed Δ, colour-coded v/c pills, congested speed,
  cordon-crossing chip) plus separate over-capacity bottleneck lists for B and A;
  job-accessibility (gravity mean A→B + population-weighted Δ%, top gainer/loser
  zones); and a road-CO₂ dispersion proxy (CBD + network totals A→B, biggest drops vs
  biggest rises = displacement, plus the displacement note). Honesty: all numbers are
  produced by a deterministic assignment model (no LLM) → stamped Simulated; auditable
  `params` + explicit `not_modelled` surfaced; honest waiting/idle/error states — never
  invents link flows when the backend is down. Fixed a percent-unit trap: the backend's
  `_pct_change` returns percent (e.g. −12.5), so the panel uses a dedicated `deltaPct`
  formatter (NOT `formatSignedPct`, which expects a 0..1 fraction) consistently across
  headline, accessibility, pollution and per-zone rows. Wired a new **Spatial** tab into
  `PanelTabs`; added ~280 lines of scoped `.sp-*` CSS (incl. a mobile-safe arc-table
  collapse) reusing theme tokens + existing `.eco-*`/`.tag.*` classes. Updated
  `frontend/README.md` endpoint map (now 23 surfaces incl. /spatial). `tsc --noEmit`
  clean, `next lint` clean (0 warnings), `next build` clean (4/4 static pages).
  **M18 complete.**
- 2026-08-13 — Verification run (roadmap complete). No unchecked ROADMAP_UI items:
  M4–M18 all shipped. Confirmed the frontend fully covers the backend: all 24
  documented endpoints are wired in `lib/api.ts` (`/health`, `/policy/compile`,
  `/baseline`, `/simulate` + `/simulate/amend`, `/parliament/debate`, `/public`,
  `/media`, `/evidence`, `/uncertainty`, `/compare`, `/optimise`, `/backtest` +
  `/backtest/example`, `/sdg`, `/diffusion`, `/registry`, `/press-conference`,
  `/ensemble`, `/institutions`, `/economy`, `/dynamics`, `/spatial`, `/microsim`),
  with the 3D-map geometry loaded from bundled static GeoJSON under
  `public/city/` (zones, roads, CBD cordon, manifest, OD pairs) so the map renders
  with no backend/`/city` dependency and degrades gracefully. Checks green:
  `tsc --noEmit` clean, `next lint` clean (0 warnings/errors), `next build` clean
  (4/4 static pages, / at 125 kB First Load JS). No UI-track work outstanding until
  the engine track ships a new endpoint to surface.

## 2026-08-13 — M19: Reproducibility tab (POST /reproduce, SPEC §32)
The engine shipped `POST /reproduce` (run reproducibility manifest, "REPRODUCE RUN")
after the UI roadmap was declared complete — the last unsurfaced documented endpoint.
Added a **Reproduce** tab exposing it end-to-end:
- `lib/api.ts`: `DatasetVersion` / `ModelVersion` / `ReproManifest` types (reusing the
  existing `AssumptionRecord` + `PolicyDSL`) and `runReproduce(policy, seed?)` with the
  standard honest-error contract (throws on non-2xx so the panel shows waiting/error, never
  a fabricated key).
- `components/twin/ReproducePanel.tsx`: policy-gated panel. Headline reproduction key
  (`run_id` + copy-to-clipboard, a *proven* reproducible ✓/✗ badge from the backend's
  twice-run digest comparison, `output_digest`, code/app version, seed, timestamp); a
  "how to reproduce" note; a SPEC §34 honesty line (no LLM prompt on the numeric path =
  `prompts` empty, and no pinned model reports LLM-touched numbers); content-addressed
  dataset versions (with `MISSING`-file guard); model versions pinned to code; and a
  collapsible pinned-assumption table. Manifest is Observed *about* the run — no invented
  numbers. Idle/loading/error states when the backend is down.
- Wired into `PanelTabs.tsx` (new `reproduce` TabKey + tab button + kept-mounted panel).
- `app/globals.css`: `repro-*` styles consistent with the Registry panel.
- `frontend/README.md`: added the endpoint to the panel↔endpoint↔SPEC map (now 19 rows)
  + a Reproduce paragraph in the honesty-contract section + the tab list in the intro.
Checks green: `tsc --noEmit` clean; `next build` clean (4/4 static pages, / at 127 kB First
Load JS). Every documented engine endpoint is again surfaced in the UI.

## 2026-08-13 — M20: Stress-testing tab (POST /stress-test + GET /stress-test/catalogue, SPEC §20)
The engine shipped the external-shock stress-testing environment (`POST /stress-test`,
`GET /stress-test/catalogue`) after the UI roadmap was declared complete — the last
unsurfaced documented endpoint. Added a **Stress** tab exposing it end-to-end:
- `lib/api.ts`: `ShockCard` / `ShockCatalogue` / `MetricStress` / `ScenarioResult` /
  `StressRobustness` / `StressReport` types (matching the real payload, verified against the
  backend TestClient) and `fetchStressCatalogue()` + `runStressTest(policy, scenarios?, horizon?)`
  with the standard honest-error contract (throws on non-2xx incl. the 404 unknown-scenario
  shape, so the panel shows waiting/error, never a fabricated robustness claim).
- `components/twin/StressPanel.tsx`: policy-gated panel. Loads the shock catalogue to render
  toggleable shock chips (each with its modelled/partial/proxy fidelity), a horizon selector
  (1/2/5/10y, confidence widens with horizon), then on run shows: a robustness roll-up banner
  (holds/degrades/fails counts + keys + headline), a no-shock baseline reference card, and a
  per-scenario card each with a verdict pill, confidence + fidelity badges, the plain-language
  caveat, a per-headline-metric stress table (Δ no-shock → Δ shocked with %, a retained-benefit
  bar with a 100%-of-baseline marker, per-metric verdict), and the exact auditable `overrides`
  (Estimated). Each shock is applied to BOTH worlds so Δ(B−A) still isolates the policy; policy
  deltas Simulated, shock magnitudes Estimated — both provenance classes surfaced. Idle/loading/
  error states when the backend is down; the currently-running server predates the endpoint, so
  the panel correctly falls back to "test the full default set" and an honest error on run.
- Wired into `PanelTabs.tsx` (new `stress` TabKey + tab button between Spatial and Institutions
  + kept-mounted panel).
- `app/globals.css`: `st-*` styles (shock chips, robustness banner, scenario cards, metric-stress
  table with retained bar, caveat/overrides) reusing theme tokens + existing `.tag`/`.eco-*` classes.
- `frontend/README.md`: added the endpoint pair to the panel↔endpoint↔SPEC map (now 24 rows),
  the tab list in the intro, and a Stress paragraph in the honesty-contract section (fidelity
  caveats + both provenance classes + retained-bar marker).
Checks green: `tsc --noEmit` clean; `next lint` clean (0 warnings); `next build` clean (4/4
static pages, / at 129 kB First Load JS). Every documented engine endpoint is again surfaced.

## 2026-08-13 — Verification run (roadmap complete, all 24 endpoints surfaced, build green)
No unchecked items remain in ROADMAP_UI.md (M4–M20 all done). Re-audited the surface area
against the live backend routers to confirm nothing new shipped for the UI to expose:
- Enumerated all `@router` decorators across `backend/app/routers/*.py` (25 routers) and
  cross-checked every path against the `fetch(`${API_BASE_URL}/…`)` calls in
  `frontend/lib/api.ts`. Every documented route is surfaced: `/health`, `/policy/compile`,
  `/baseline`, `/simulate` (+`/simulate/amend`), `/parliament/debate` (+`/parliament/failure-modes`),
  `/public`, `/media`, `/evidence`, `/uncertainty`, `/compare`, `/optimise`, `/backtest`
  (+`/backtest/example`), `/sdg`, `/diffusion`, `/registry`, `/reproduce`, `/press-conference`,
  `/ensemble`, `/institutions/review`, `/economy`, `/dynamics`, `/spatial`, `/microsim`,
  `/stress-test` (+`/stress-test/catalogue`). No unsurfaced engine endpoint found.
- Checks green: `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 129 kB
  First Load JS, 0 lint warnings).
- Live-backend smoke test not possible this run: port 8000 is held by an unrelated service
  (returns an OpenAI/vision/mongo health payload, not the twin's `HealthResponse`), so the
  twin backend isn't up. That is exactly the "waiting for backend" path the panels handle;
  starting the backend is the engine track's domain, so left untouched. No numbers fabricated.

## 2026-08-13 (11:32 UTC) — Verification run (roadmap complete, build green, no new endpoints)
Re-ran the full check after the prior verification. No unchecked items in ROADMAP_UI.md (M4–M20
all done). Re-audited surface area against the live backend:
- Enumerated all 24 non-health routers under `backend/app/routers/*.py` (via router prefixes +
  `include_router` in `main.py`) and cross-checked each documented path against `lib/api.ts` —
  all 25 paths (incl. `/simulate/amend`, `/backtest/example`, `/stress-test/catalogue`) resolve.
  No unsurfaced engine endpoint found.
- `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 129 kB First Load JS).
- Live smoke test still not possible: port 8000 is held by an unrelated OpenAI/vision service
  (not the twin `HealthResponse`), so the twin backend isn't up. Starting it is the engine
  track's domain; panels correctly show their "waiting for backend" states. No numbers fabricated.

## 2026-08-13 (11:38 UTC) — Verification run (roadmap complete, build green, backend still down)
Cron run; no unchecked items in ROADMAP_UI.md (M4–M20 all done). Re-audited surface area and
re-ran the build:
- Enumerated all 23 router prefixes in `backend/app/main.py` `include_router` calls and
  cross-checked each against the `fetch(`${API_BASE_URL}/…`)` paths in `frontend/lib/api.ts`.
  Every backend prefix is surfaced (health, policy, baseline, simulate[+/amend], parliament
  [debate+failure-modes], public, media, evidence, uncertainty, compare, optimise, backtest
  [+/example], sdg, diffusion, registry, reproduce, press-conference, ensemble, institutions
  /review, economy, dynamics, spatial, microsim, stress-test[+/catalogue]). No new endpoint.
- `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 129 kB First Load JS).
- Live smoke test still blocked: `GET :8000/health` returns an unrelated OpenAI/vision service
  payload (`provider:"openai"`, `gpt-4o-mini`, not the twin `HealthResponse`) and `/baseline`
  404s — the twin backend isn't running on that port. Starting it is the engine track's domain;
  panels correctly show their "waiting for backend" states. No numbers fabricated.

## 2026-08-13 (11:46 UTC) — Verification run (roadmap complete, build green, backend still down)
Cron run; ROADMAP_UI.md has 0 unchecked / 33 checked items (M4–M20 all done). Re-audited
surface area against the live backend code and re-ran the checks:
- All 24 `include_router()` calls in `backend/app/main.py` enumerated and every route decorator
  (incl. the multi-line ones: `/simulate/amend`, `/parliament/failure-modes`,
  `/institutions/review`, `/backtest/example`, `/stress-test/catalogue`) cross-checked against
  the `fetch(`${API_BASE_URL}/…`)` paths in `frontend/lib/api.ts`. Every backend route resolves
  to a UI surface; no unsurfaced engine endpoint. No new endpoint since 11:38.
- `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 41.8 kB / 129 kB First Load JS,
  no lint warnings).
- No TODO/FIXME markers anywhere under `app/`, `components/`, `lib/`.
- Live smoke test still blocked: `GET :8000/health` returns an unrelated OpenAI/vision service
  (`provider:"openai"`, `gpt-4o-mini`) and `/baseline` 404s — the twin backend isn't running on
  that port. Starting it is the engine track's domain; panels correctly show their "waiting for
  backend" states. No numbers fabricated.

## 2026-08-13 (11:56 UTC) — Verification run (roadmap complete, build green, backend still down)
Cron run; ROADMAP_UI.md 0 unchecked / 33 checked (M4–M20). Re-audited engine surface vs UI:
- All 25 `include_router()` calls in `backend/app/main.py` enumerated; every route decorator
  (incl. multi-line `/simulate/amend`, `/parliament/*`, `/institutions/review`,
  `/backtest/example`, `/stress-test/catalogue`) cross-checked against the fetch paths in
  `frontend/lib/api.ts`. 24 prefixes wired in api.ts + `/health` (HealthStatus) = 25/25. No
  unsurfaced engine endpoint; no new endpoint shipped since M20 (engine has only added tests).
- `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 41.8 kB / 129 kB First Load).
- 0 TODO/FIXME/XXX markers under `app/`, `components/`, `lib/`.
- Live smoke test still blocked: `GET :8000/health` returns an unrelated OpenAI vision service
  (`provider:"openai"`, `gpt-4o-mini`), `/baseline` 404s — the twin backend isn't on that port.
  Starting it is the engine track's job; panels correctly show "waiting for backend". No numbers
  fabricated.

## 2026-08-13 (12:10 UTC) — LIVE end-to-end contract verification (backend brought up locally)
Roadmap complete (M4–M20, 33/33). Instead of another static green-build note (prior 5 runs
couldn't reach a backend — port 8000 is held by an unrelated OpenAI/vision service), I stood
the **twin backend up myself** on a free port (`.venv/bin/uvicorn app.main:app :8137`, read-only,
no backend files touched) and ran a real contract smoke test replicating the exact requests
`frontend/lib/api.ts` sends:
- **28/28 UI-consumed endpoints returned HTTP 200 with the expected top-level shape.** Every
  route the typed client calls — `/health`, `/baseline`, `/policy/compile`, `/simulate`,
  `/parliament/debate` + `/failure-modes`, `/public`, `/evidence`, `/media`, `/sdg`, `/diffusion`,
  `/backtest`(+`/example`), `/ensemble`, `/press-conference`, `/optimise`, `/uncertainty`,
  `/compare`, `/institutions/review`, `/registry`, `/economy`, `/dynamics`, `/microsim`,
  `/spatial`, `/reproduce`, `/stress-test`(+`/catalogue`), `/simulate/amend` — resolved live and
  carried the keys the panels destructure (e.g. `simulate.delta`, `compare.headline_table`,
  `reproduce.run_id`, `stress-test.robustness`). Bodies matched the client exactly (incl.
  `metric_key` discovery via the 404 `available_metric_keys` path → `mode_share.car_pct`).
- **Honesty contract holds against real data:** `/media` disclaimer = "SIMULATED — NOT A REAL
  ARTICLE OR FORECAST OF A SPECIFIC OUTLET" with Generated/Simulated tags; `/simulate` delta
  series carries per-point `low`/`high` uncertainty bands (SPEC §34). No fabricated numbers.
- `tsc --noEmit` exit 0; `next build` clean (4/4 static pages, / at 41.8 kB / 129 kB First Load);
  `next lint` — no warnings/errors. No new engine endpoint since M20 (24 routers, all surfaced).
- Backend was shut down after the test (running it is the engine track's domain); the UI's
  "waiting for backend" states remain correct when it's down. No files outside `frontend/**` +
  this progress file were modified.

## 2026-08-13 (12:35 UTC) — M21: Historical-analogue / causal layer tab (SPEC §7.1/§8)
The engine shipped `POST /analogues` (+ `GET /analogues/cases`, router `analogues.py`, commit
8c753cb) after M20 declared the UI roadmap complete — an unsurfaced endpoint. Added the **Analogue**
tab, the last uncovered engine surface.
- `lib/api.ts`: `HistoricalCase`, `CaseEstimate`, `StructuralComparison`, `AnalogueEstimate`
  interfaces + `runAnalogues(policy, horizonMonths?, includeStructuralComparison?)` (POST) and
  `fetchAnalogueCases()` (GET). Throw-on-non-OK so the panel shows an honest waiting/error state,
  never a fabricated figure (SPEC §34).
- `components/twin/AnaloguePanel.tsx`: transfer-weighted central estimate + confidence band
  (widens when analogues weak/disagree), analogue-quality (strong/moderate/weak) + transferability
  pills; a DiD range chart (each pooled scheme's effect, marker opacity = pool weight, over the
  highlighted pooled CI + central line, zero-line); the **structural cross-check** card — agent-based
  `structural_effect_pct` tagged Simulated vs analogue `analogue_effect_pct` tagged Estimated + signed
  gap + agreement pill (consistent/moderate-gap/large-gap) + interpretation (SPEC §8 "real cordons
  rarely exceed ~30%" sanity floor); contributing-cases table (DiD, identification, transfer, weight;
  context-only schemes greyed at weight 0); identification diagnostics; collapsible `not_modelled`.
  Honest "no comparable scheme" state for transit-only/other policies. Historical outcomes Observed
  (illustrative), transfer Estimated — both classes surfaced.
- `PanelTabs.tsx`: registered the `analogue` tab (label "Analogue") between Stress and Institutions;
  panel stays mounted like the others. `globals.css`: scoped `.anl-*` styles (own prefix — the
  existing `.analogue-*` classes belong to EvidenceDrawer, no collision), mobile-safe.
- **Live contract check** (stood the twin backend up read-only on port 8139, no backend files touched):
  `/analogues` returned HTTP 200 with every key the panel destructures; a £15/day cordon+reinvest
  policy pooled 8 cases → quality "strong", est −21.69% (CI −54.12…0.0), transferability 0.758, and
  the structural cross-check flagged agreement="large gap" (ABM −92.68% vs analogue −21.69%, gap
  −70.99 pts) — exactly the SPEC §8 honesty story the card exists to tell. `/analogues/cases` → 8
  cases, tag Observed. Backend shut down after (running it is the engine track's domain).
- `tsc --noEmit` exit 0; `next build` clean (4/4 static, / at 46.7 kB / 134 kB First Load); `next lint`
  no warnings/errors. Only `frontend/**` + ROADMAP_UI.md + this file touched. Every documented engine
  endpoint is now surfaced in the UI (25 routers incl. `/health`).

## 2026-08-13 (12:45 UTC) — M22: Time-series forecast tab (SPEC §7.2)
The engine shipped `POST /timeseries` (router `timeseries.py`, commit 6119420) after M21
declared the UI roadmap complete — a newly unsurfaced endpoint. Added the **Time-series** tab.
- `lib/api.ts`: `ForecastPoint`, `FitDiagnostics`, `MetricForecast`, `TimeSeriesForecast`
  interfaces + `runTimeseries(policy)` (POST). Throw-on-non-OK so the panel shows an honest
  waiting/error state, never a fabricated trajectory (SPEC §34).
- `components/twin/TimeseriesPanel.tsx`: per-metric selector chips; an SVG chart overlaying the
  seeded **synthetic monthly history** (Simulated, muted line on the negative-time axis), the
  **World A** baseline forecast (Estimated; trend + 12-month seasonal + AR(1)), and the **World B**
  policy trajectory (Simulated; World A × the ABM Δ(B−A)), each as nested 80%/95% prediction bands
  that visibly widen toward year 10, plus central lines and a "now → forecast" divider; a headline
  strip (World A vs World B central @ final horizon with 80% bands + signed policy-shift Δ%); an
  auditable fit-diagnostics grid (level, trend/month, seasonal amplitude, AR(1) φ, residual σ,
  in-sample MAPE + honest held-out MAPE, method string); a per-horizon policy-shift row; a
  collapsible assumptions table + `not_modelled` scope list. Three provenance classes on one chart —
  history Simulated, statistical baseline Estimated, policy shift Simulated — all surfaced.
- `PanelTabs.tsx`: registered the `timeseries` tab (label "Time-series") between Analogue and
  Institutions; panel stays mounted like the others. `globals.css`: scoped `.ts-*` styles (own
  prefix; no clash with `.tab`/`.tag`), World A = accent blue, World B = ok green, history = muted,
  mobile-safe.
- **Live contract check** (stood a fresh twin backend up read-only on port 8156, no backend files
  touched; pre-existing :8139/:8000 left alone): `/timeseries` returned HTTP 200 with every key the
  panel destructures. A £15/day cordon+reinvest policy → 8 metrics × 8 checkpoints; car-mode-share
  fit MAPE 0.48% in-sample / 0.61% held-out, tags history=Simulated / world_a=Estimated /
  world_b=Simulated, policy shift ramping 0 → −34.09% by year 10, and the 95% band widening
  0.648 → 2.933 across the horizon — exactly the "uncertainty grows with horizon" story the layer
  exists to tell (SPEC §7.2/§8). Fresh backend shut down after (running it is the engine track's
  domain).
- `tsc --noEmit` exit 0; `next build` clean (4/4 static, / at 49 kB / 137 kB First Load); `next lint`
  no warnings/errors. Only `frontend/**` + ROADMAP_UI.md + this file touched. Every documented engine
  endpoint is now surfaced in the UI (26 routers incl. `/health`).

## 2026-08-13 (12:57 UTC) — M23: Data-fabric provenance tab (SPEC §4)
- **Context:** engine mounted a new router, `GET /data-fabric` (`backend/app/routers/datafabric.py`,
  written 12:48 UTC — after M22 declared the UI roadmap complete). It's the dataset-level provenance
  layer SPEC §4 asks for: a machine-readable catalogue of every dataset the engine reads, each with
  the full §4 metadata record built *live from the file bytes* (record counts, missingness, a
  content-hash `revision`), plus the supported-format contract and the harmonisation-pipeline lineage.
  Complements — doesn't duplicate — the metric-level `/evidence` trace (§26), the `/registry` model
  catalogue (§33) and the per-run `/reproduce` envelope (§32). No UI surfaced it → added M23.
- `lib/api.ts`: typed the payload (`DataFabric`, `DatasetCard`, `VariableCard`, `TransformationStep`,
  `FormatSupport`, `HarmonisationStep`) + `getDataFabric()` — a `GET` with `cache: "no-store"` that
  throws on non-2xx so the panel can show an honest error state instead of inventing a catalogue.
- `components/twin/DataFabricPanel.tsx` (new): policy-independent, loads on mount. Renders the §4
  `input data → transformation → model → assumptions → result` lineage contract; a summary-counts
  strip; and a collapsible card per dataset with an auditable file-facts grid (format, records,
  missingness with a warn tone, the content-hash revision shown mono, scope/resolution/frequency/
  period/units/license), a confidence line, the variable table (name/type/description/missing-%), the
  ordered transformation history (each step tagged), and the real-world analogues labelled
  *schema-compatible with (not a live source)* to keep the synthetic-city honesty. Also the
  supported-ingestion-format chips (native/adapter-ready/declared) and the harmonisation stages
  (implemented ✓ / declared ○ + code path). Manifest tag `Observed` about the data; datasets
  Simulated/assumption-set. `idle`/`loading`/`error` states with a Retry.
- `PanelTabs.tsx`: registered the `datafabric` tab (label "Data Fabric") after Reproduce; panel stays
  mounted like the others. `globals.css`: scoped `.fabric-*` styles (own prefix; no clash with
  `.tab`/`.tag`), mobile-safe (variable grid collapses at 640px).
- **Contract check:** the twin backend wasn't reachable on the shared host (a *different* service
  answers on :8000), so I verified the response shape directly against the engine source — ran
  `backend/.venv/bin/python -c "from app.datafabric.model import build_data_fabric; ..."` (read-only,
  no backend files touched). Confirmed every key the panel destructures: 6 datasets (5 synthetic + 1
  assumption-set), `records_total` 12,246, per-dataset `revision` like `sha256:99337d934bd8`,
  `missingness` 0.0, variable cards with `missing_pct`, transformation steps tagged `Simulated`,
  and `provenance` `Observed`. Field names/types match the TS interfaces exactly.
- `tsc --noEmit` exit 0; `next build` clean (4/4 static, / at 50.8 kB / 138 kB First Load). Only
  `frontend/**` + ROADMAP_UI.md + this file touched. Every documented engine endpoint (27 routers
  incl. `/health`) is now surfaced in the UI.
- 2026-08-13 — M24: Run tab — surfaced the scenario orchestrator `POST /run`
  (SPEC §28/§29, the killer demo), the last unsurfaced engine endpoint. Added
  `runScenario()` + `RunResponse`/`RunHeadlineMetric`/`NarrativeBeat`/
  `RunProposedAmendment` types to `lib/api.ts` and a new `RunPanel` (first tab).
  One call composes compile → simulate → public → parliament → amendment
  re-sim → media into a mutually-consistent view: consistency banner (numbers
  Simulated · prose Generated · no LLM in numeric path), §29 narrative beats,
  composed outcomes dashboard at a selectable horizon (World A→B, signed Δ+%,
  band, provenance chip, good/bad by metric), net-support gauge, parliament
  snapshot (motion+tally+summary), amendment block with the isolated
  Δ(amended−original) table at the final checkpoint (≈0 rows honest), and a
  SIMULATED-stamped press snapshot. Drives from the store's compiled policy or a
  natural-language fallback box; honest idle/loading/error states, never
  fabricates a narrative. `tsc --noEmit` + `next build` clean. Every documented
  engine endpoint now has a UI surface.

## 2026-08-13 — M25: Change-assumptions-and-rerun tab (SPEC §34.10)
- Surfaced the last unwired endpoint pair `GET /assumptions` +
  `POST /assumptions/rerun` — SPEC §34's tenth guardrail ("users can change the
  model's input assumptions and re-run"), the interactive complement to the §24
  uncertainty fan (which sweeps the *same* knobs and only ranks them).
- New `AssumptionsPanel.tsx`: loads the overridable-knob catalogue live from the
  code (retryable waiting/error state), renders one slider per assumption bounded
  to its documented [low, high] with a live default marker; dragging off default
  pins it. Contrast-horizon selector (Y1/Y2/Y5/Y10). Re-run posts only the pinned
  overrides and shows (a) an applied-overrides list echoing default → applied with
  an honest **clamped-to-range** flag + note when a request left the band, and
  (b) a per-metric contrast table: Δ(B−A) under default vs overridden assumptions,
  the signed shift (effect of the change) with a scaled bar + %-of-default,
  good/bad-coloured by metric direction (only transit is up=good), ≈0 shown as
  "no change".
- Honesty: inputs tagged Estimated, the re-run Simulated (deterministic, same
  pipeline `/simulate` runs, no LLM on the numeric path); catalogue is the exact
  §24 `ASSUMPTIONS` registry so the two can never disagree; idle (no policy) /
  loading / waiting (catalogue down) / error states, never fabricates a contrast.
- `lib/api.ts`: added `AssumptionCard`, `AssumptionCatalogue`, `AppliedOverride`,
  `MetricContrast`, `AssumptionRerunResult` types, `UnknownAssumptionError`, and
  `getAssumptions()` / `rerunAssumptions()`. Wired the tab into `PanelTabs.tsx`;
  added `asm-*` styles to `globals.css` (mobile-safe). `tsc --noEmit` + `next build`
  clean. ROADMAP_UI now 38/38.
- Follow-up: none open — every documented engine endpoint has a UI surface again.

## 2026-08-13 — M26: Grand counterfactual A/B/C/D tab (SPEC §21/§22)
- Surfaced the engine's newest endpoint `POST /compare/grand` — the canonical §21
  four-way comparison the plain Compare tab never composed. `/compare` takes
  arbitrary caller amendments; the grand endpoint names the quartet by role
  (A baseline / B policy / C opposition amendment / D URBAN-optimised), auto-derives
  World C, wires the §22 optimiser in as World D, and adds a `derivation` audit.
- New `GrandComparePanel.tsx`: drives off the store's compiled policy with a
  Time-Machine horizon selector (Y1/Y2/Y5/Y10) and a World-D optimiser-target
  selector (best-balanced / cut-emissions-20% / protect-low-income — each a
  transparent objective+constraints pair). Renders a consistency banner (one
  deterministic model, four worlds; C/D re-simulated through the same path as B;
  no new numeric model, no LLM), role-coloured A/B/C/D world chips, the headline
  table (baseline value + each world's value + Δ-vs-baseline per metric at the
  horizon), and the **derivation audit**: a World C card (amendment source
  caller/auto-derived + structured edits + rationale, or an honest "no amendment
  applies" state) and a World D card (which optimiser recommendation slot was
  picked, objective/constraints, feasibility + candidate counts, and the chosen
  config re-expressed as concrete policy edits).
- Honesty: every world Simulated (deterministic, re-simulated identically to B);
  amendment/optimiser inputs Estimated — both provenance classes surfaced; World A
  always present; `idle` (no policy) / `loading` / `error` states when the backend
  is down, never fabricates a comparison.
- `lib/api.ts`: extended `CounterfactualComparison` with the optional `derivation`
  block, added `OptimiserCandidateConfig`, `GrandWorldC`, `GrandWorldD`,
  `GrandDerivation`, `GrandCompareRequest` types and `runGrandCompare()`. Wired the
  tab into `PanelTabs.tsx` (label "Grand A/B/C/D", next to Compare); added `grand-*`
  + `.cmp-world.optimised` styles to `globals.css` (mobile-safe). `tsc --noEmit` +
  `next build` clean. ROADMAP_UI now 39/39.
- Follow-up: none open — every documented engine endpoint has a UI surface again.

## 2026-08-13 — M27: Baseline World Model tab (GET /world, SPEC §5/§28.2)
Surfaced the new `GET /world` endpoint (engine committed 30e61a2) that the UI had
no view for. Added `WorldModel` types + `getWorld()` client to `lib/api.ts`; new
`WorldPanel.tsx` renders World A's six SPEC §5 layers — Population (stat grid +
income/age/household/occupation share bars + Estimated behavioural priors),
Economy (jobs + sector/wage bars), Geography (network/zone/building stat grid +
land-use/road-class/building-type bars), Environment (commuter-CO₂ + green space +
water-layer flag + land-use bars), Institutions (Observed Parliament §11 +
reviewer §18 agent chips) and Society (Estimated −1…+1 opinion priors by income
band, media-environment chips §15, civic-actor cards §14). Each layer card shows
its own provenance chip and a collapsible honest `not_modelled` list. New `world`
tab wired into `PanelTabs.tsx` (2nd slot, after Run); ~230 lines of `world-*` CSS.
Verified against the live backend payload (7,985 agents, 81 zones, 144 road links,
etc.); provenance honesty preserved — structural counts Simulated, institutions
Observed, society priors Estimated, no LLM on any number, honest loading/error
states. `tsc --noEmit` clean; `next build` clean (/ = 59.7 kB). ROADMAP_UI.md M27
checked off. Note: the currently-running dev backend predates `/world`, so it 404s
live until the engine process restarts — the tab shows its honest error+retry
state until then, exactly as designed.

## 2026-08-13 — Verification checkpoint (UI track, roadmap complete)
No unchecked items remain in ROADMAP_UI.md (39/39 through M27). Audited every real
backend route against the frontend and confirmed each has a live surface:
`/health /baseline /policy/compile /simulate /simulate/amend /compare /compare/grand
/parliament/debate /parliament/failure-modes /public /media /evidence /registry
/reproduce /uncertainty /optimise /economy /dynamics /diffusion /microsim /spatial
/sdg /analogues/cases /backtest /stress-test /catalogue /timeseries /data-fabric
/run /assumptions /assumptions/rerun /world` — one panel each under
`frontend/components/twin/*` (plus the map + evidence drawer). The only unmatched
routes are the FastAPI starter-template leftovers (`/items` `/users` `/login`
`/uploadfile` `/files` `/send-notification`), which are not part of the SPEC surface.
Health: `tsc --noEmit` clean, `next build` clean (/ = 59.7 kB, First Load 147 kB).
Live re-verification against the urban backend was not possible this run — port 8000
is currently held by an unrelated service (a vision/STT app), not the urban-policy-twin
API, so the twin's endpoints 404. That's the designed-for case: every tab shows its
honest `waiting/error` state rather than minting numbers (SPEC §34). Nothing new to
surface — the engine roadmap is likewise complete (42 routes) and every one is exposed.
No code change this checkpoint; UI track is caught up and green.

## 2026-08-13 — M28: guided demo now reaches the killer Run + Reproduce beats
Roadmap re-verified complete (M1–M27, all 42 backend routes surfaced) and both
`tsc --noEmit` + `next build` were green on entry — but the SPEC §29 guided tour
(`lib/demo.ts`) predated the newest flagship tabs and ended at Registry, so a judge
taking the walkthrough never saw **Run** (M24, the whole pipeline composed into one
mutually-consistent call — §28/§29) or **Reproduce** (M19, the content-addressed run
receipt — §32). Extended the tour: inserted a Run step after Red Team ("the whole
pipeline in one call": compile→simulate→public→parliament→amendment→press all reading
one simulation, so the dashboard/tally/amendment-Δ/SIMULATED press can't disagree;
numbers Simulated, prose Generated, no LLM on the numeric path), and added a closing
Reproduce step ("the content-addressed receipt": run id, output digest, pinned
code/data/seeds, proven-reproducible badge from the backend's twice-run digest diff).
Widened `DemoTab` with `run`/`reproduce` (both already `PanelTabs` TabKeys → tab
switching stays type-safe), renumbered captions to 7/8/9, left the generic `DemoTour`
renderer and `[data-tour="tabs"]` anchor untouched. Tour still renders zero metrics
(SPEC §34 — pure guidance over the real UI or its honest `waiting` state). `tsc
--noEmit` clean, `next build` clean (/ = 60 kB, First Load 148 kB). No backend/data/
engine files touched.

## 2026-08-13 — M29: surface the North-Star answer (SPEC §37, the flagship)
Roadmap re-verified complete on entry (M4–M28, `tsc --noEmit` + `next build`
both green) — but the engine had shipped one new endpoint the UI hadn't surfaced:
`POST /north-star` (SPEC §37 — *the* URBAN experience). A minister asks "What
happens if we implement this?" and the backend answers with the fixed, ordered
15-line §37 narrative (baseline → analogues → mechanisms → median outcome →
uncertainty → winners → losers → failure modes → opposition's strongest argument
→ opinion evolution → media → three risk-reducing amendments → each amendment's
effect → best-fit config → every assumption). It composes existing deterministic
layers verbatim (no new numeric model), so the answer can never disagree with the
deep tabs.
Added the **North-Star tab** as the flagship (first) analysis tab:
- `lib/api.ts`: `NorthStarSection`, `NorthStarProposedAmendment`, `NorthStarAnswer`,
  `NorthStarRequest` types + `runNorthStar()` client (POST /north-star, JSON-detail
  error handling like `/run`). All backing objects reuse the already-exported typed
  interfaces (BaselineSnapshot, AnalogueEstimate, EventLedger, RunHeadlineMetric,
  DeltaTimeSeries, UncertaintyResult, MicrosimReport, FailureModeRegister, Argument,
  DebateResponse, DiffusionResult, MediaResponse, AmendmentComparison, OptimiserResult)
  so the tab can never drift from the standalone endpoints' shapes.
- `components/twin/NorthStarPanel.tsx`: compiled-policy-or-NL-fallback input +
  Time-Machine horizon selector; provenance banner (Simulated numbers · Estimated
  transfers · Generated prose · no LLM in numeric path); minister's-question echo;
  the ordered §37 narrative (per line: question + deterministic one-sentence
  synthesis + provenance chip + `backs` code + cross-link to the deep tab that
  carries the evidence); the composed median-outcome dashboard tiles at the chosen
  horizon (World A→B, signed Δ+%, band, provenance chip, good/bad colouring); the
  risk-reducing amendment cards (label + targeted risk + rationale + isolated
  Δ(amended − original) table, ≈0 rows shown as "no change"); and the §37.15
  assumptions/guardrail footer (assumption + data-source counts, SPEC §34 guardrail
  pass/fail tally, the explicit "no LLM produces any figure" honesty line read off
  `evidence.llm_touches_numbers`, and the guardrail checklist). `idle`/`loading`/
  `error` states throughout — never mints a narrative when the backend is down.
- `components/twin/PanelTabs.tsx`: registered `northstar` TabKey + "North-Star"
  tab (placed first) + always-mounted panel.
- `app/globals.css`: `.ns-*` styles for the question echo, the ordered narrative
  rows, the amendment cards and the evidence footer; reuses the `.run-*`
  controls/consistency/tiles/amendment scaffolding for consistency.
Health: `tsc --noEmit` clean, `next build` clean (/ = 61.7 kB, First Load 149 kB).
Live verification against the running backend wasn't possible this run (port 8000
still held by an unrelated app, so `/north-star` 404s) — the tab shows its honest
error+retry state exactly as designed (SPEC §34). No backend/data/engine files
touched. Every documented engine route (43 now) has a UI surface again.

## 2026-08-13 — M29 follow-up: North-Star is now the guided-tour capstone
Extended the SPEC §29 guided tour (`lib/demo.ts`) with a closing **step 10** after
Reproduce that spotlights the new North-Star tab and frames it as the §37
culmination: every layer the judge just walked through (baseline, analogues,
mechanisms, median outcome, uncertainty, winners/losers, failure modes,
opposition, opinion, media, risk amendments + effects, best-fit config,
assumptions) fused into the single ordered answer to the one question that
started it — "What happens if we implement this?" — with nothing new computed, so
it can't disagree with the tabs behind it. Widened `DemoTab` with `northstar`
(already a `PanelTabs` TabKey → tab switching stays type-safe); the generic
`DemoTour` renderer and `[data-tour="tabs"]` anchor are untouched. The tour still
renders zero metrics (pure guidance, SPEC §34). `tsc --noEmit` clean, `next build`
clean (/ = 61.9 kB, First Load 150 kB). Frontend-only.

## 2026-08-13 — UI-track: M30 — re-sync frontend README with the 28-tab surface
Roadmap was 43/43 complete and every backend route (43 routes / 33 routers) already
had a UI tab, so no new endpoint to surface. Fixed the one real drift: the
`frontend/README.md` "Analysis surfaces → endpoint → SPEC" table still described the
~18-endpoint era and its "every documented backend endpoint has a UI surface" claim
had gone stale — eight flagship tabs (World, Run, North-Star, Grand A/B/C/D, Analogues,
Time-series, Data Fabric, Change-assumptions-and-rerun) were missing from the map. A
judge reading the README got a smaller app than the one they click, which is a §34
honesty gap. Rewrote the intro surface list and the endpoint→SPEC table to cover all 28
analysis tabs in tab-bar order (North-Star/Run first as the §37/§29 flagships), with
exact paths verified against `lib/api.ts` (`/institutions/review`,
`/parliament/failure-modes`, `/compare/grand`, `/assumptions/rerun`, `/data-fabric`, …)
and correct SPEC sections (§37, §5/§28.2, §7.1/§7.2, §21/§22, §4, §34.10). Docs only —
no code change; `tsc --noEmit` clean, `next build` clean (/ = 61.9 kB, First Load 150 kB).
Frontend-only.

## 2026-08-13 — UI-track: verification checkpoint — roadmap complete, full surface green
No unchecked items remain in `ROADMAP_UI.md` (44/44 checked, M4→M30) and the engine
roadmap is likewise complete, so there was no new endpoint to surface this run.
Ran the health sweep instead: enumerated all backend routes (38 paths across 34
routers) and cross-checked each exact path string against the frontend source — all
38 are referenced from `lib/api.ts`, so the "every documented backend endpoint has a
UI surface" claim still holds. `npx tsc --noEmit` clean; `npx next build` clean
(compiled successfully, 4/4 static pages, / = 61.9 kB, First Load 150 kB). No code
change — a green-state confirmation to keep progress visible while both tracks sit at
feature-complete. Frontend-only.

## 2026-08-13 — UI-track: verification checkpoint — honesty audit + full-surface green
Roadmap remained 44/44 complete (M4→M30) with the engine roadmap also feature-complete,
so no new endpoint to surface. Went beyond the prior route/build checkpoint with a SPEC §34
honesty audit: (1) programmatically enumerated all 38 mounted backend routes (incl. multi-line
decorators like `/north-star`, `/compare/grand`, `/simulate/amend`, `/parliament/failure-modes`,
`/institutions/review`, `/assumptions/rerun`) and confirmed every one is referenced from
`frontend/lib` (0 missing); (2) scanned all components/lib/app for hardcoded/fabricated/dummy
metrics — every hit is a legitimate, clearly-labelled waiting/placeholder state (e.g. map
traffic/support overlays carry an explicit `"Placeholder"` provenance class, MetricTile/Dashboard
show "Awaiting model / Awaiting /simulate"), never an invented number presented as real. Build
green: `npx tsc --noEmit` clean, `npx next build` compiled successfully (4/4 static pages,
/ = 61.9 kB, First Load 150 kB). No code change — a green-state + honesty-contract confirmation.
Frontend-only.

- 2026-08-13 — M31: Surfaced the global sensitivity tornado (`POST /sensitivity`,
  SPEC §24/§26) — the one endpoint the UI hadn't surfaced after the engine shipped
  it. New `SensitivityPanel.tsx` (tab "Sensitivity", placed after Uncertainty in the
  tab bar) drives the compiled policy through a Time-Machine horizon selector and
  renders: a consistency banner (deterministic re-runs at documented assumption edges,
  no LLM, bar-length = leverage-not-likelihood, interactions are the Uncertainty fan's
  job, same overridable set as the Uncertainty tab), the `headline`, a
  "what-the-answer-rests-on" aggregate driver ranking (mean influence-share leverage
  bars, greyed "no effect here" rows for assumptions flat on this policy), and per-metric
  tornado cards (provenance tag + default Δ(B−A) + most-influential assumption + signed
  low→high bars with a default-Δ marker and swing/%-of-default, up/down coloured, flats
  collapsed to a count), plus a collapsible §34 scope-limits list. Added typed
  `AssumptionSwing`/`MetricTornado`/`AssumptionDriver`/`SensitivityResult` + `runSensitivity()`
  to `lib/api.ts` (shapes matched verbatim to backend `sensitivity/schema.py`), wired the
  tab into `PanelTabs.tsx`, and added scoped `.sens-*` CSS to `globals.css`. Analysis
  Estimated, underlying metrics Simulated, no LLM on the numeric path; honest
  idle/loading/error states — never fabricates a tornado when the backend is down (the
  live :8000 here is a different app, so the tab correctly shows its waiting state).
  Green: `npx tsc --noEmit` clean, `npx next build` compiled (4/4 static pages, / = 63.3 kB,
  First Load 151 kB). Frontend-only.

- 2026-08-13 — M32: Citizen View tab (`POST /citizen` + `GET /citizen/sample`, SPEC §17/§31).
  The engine shipped the single-household drill-down after M31 completed the roadmap; this is
  the UI surface. Added typed `CitizenView`/`CitizenSnapshot`/`AgentState`/`CitizenProfile`/
  `CitizenSample` types + `runCitizen()`/`getCitizenSample()` to `lib/api.ts`, a new
  `CitizenPanel.tsx`, and wired a "Citizen" tab into `PanelTabs` (after World). Panel: a
  policy-independent "click a household" picker + five archetype selectors; on run, a profile
  card, before→after topline tiles (commute / cost / §31 support gauge with stance colouring),
  the Time-Machine table (World-A row + each checkpoint's mode, commute+cost widening bands,
  charge, support), the deterministic "Why?" narrative, a collapsible §31 Agent-State table,
  and `not_modelled`. All Simulated (reuses `/simulate` mode-choice + `/public` opinion model,
  no LLM); honest idle/loading/error + picker-unavailable fallback. Added `.cit-*` CSS.
  Green: `npx tsc --noEmit` clean, `npx next build` compiled (4/4 static, / = 65.8 kB,
  First Load 153 kB). Frontend-only.

- 2026-08-13 — M33: Business View single-firm drill-down tab (SPEC §17 Business View).
  Surfaced the engine's new `POST /business` (+ `GET /business/sample`) — the one endpoint
  the UI hadn't surfaced after M32. New `BusinessPanel.tsx` mirrors the Citizen drill-down:
  archetype selectors (representative / most-exposed / biggest-footfall-loss /
  pedestrian-winner / largest) + a policy-independent "click a firm" picker; then per-firm
  profile card, before→after topline tiles (daily footfall, labour-access index, deliveries,
  added annual cost with band, net revenue-proxy Δ%), the Time-Machine trajectory table
  (World-A row + widening footfall/cost/revenue bands), deterministic adaptation-decision
  cards, "Why?" narrative, and collapsible not_modelled scope-limits. Honesty (SPEC §34):
  physical drivers Simulated (same mode-choice model as /simulate), firm translation Estimated
  (same /economy coefficients), revenue explicitly an Estimated proxy (before/after ratio, not
  turnover), no LLM on the numeric path; honest idle/loading/error + picker-unavailable
  fallback. Added `lib/api.ts` types+fns (FirmProfile/FirmSnapshot/BusinessView/FirmSample,
  BUSINESS_SELECTORS, getBusinessSample, runBusiness), wired the tab into PanelTabs after
  Citizen, added a small `.biz-*` CSS block (reuses `.cit-*` for shared structure).
  Green: `npx tsc --noEmit` clean, `npx next build` compiled (4/4 static, / = 67.5 kB,
  First Load 155 kB). Frontend-only; 29 analysis tabs now surface all 39 documented endpoints.

- 2026-08-13 — M34: re-sync frontend/README.md with the Citizen + Business drill-downs.
  README's surface map was last synced at Sensitivity (29 surfaces); Citizen (M32) and
  Business (M33) shipped after, so the intro count and endpoint table under-claimed and the
  "every documented backend endpoint has a UI surface" line was stale. Bumped the intro to 31
  surfaces + listed the two drill-downs, and added `POST /citizen`+`GET /citizen/sample`
  (§17/§31) and `POST /business`+`GET /business/sample` (§17) rows in tab-bar order. Docs
  only; verified all 44 backend paths are referenced in lib/api.ts (0 unsurfaced).

- 2026-08-13 — M35: accessible, filterable analysis tab bar (SPEC §27 usability + a11y).
  The lower-deck tab bar had reached 31 panels but was a flat row of plain buttons that
  only *declared* `role="tablist"`/`role="tab"` — no keyboard pattern, no tab↔panel links,
  no way to find a panel by name. Rewrote `PanelTabs.tsx` to the WAI-ARIA APG Tabs pattern:
  roving `tabIndex` (single tab stop), Arrow/Home/End navigation with automatic activation
  over only the visible tabs (wrapping), each tab wired to its panel via `id` +
  `aria-controls` + `aria-labelledby`, active `tabpanel` focusable, plus a visible
  `:focus-visible` ring. Added a `type=search` filter box (sr-only label, live matched/total
  count, "No panel matches …" status) that narrows the 31 tabs by label while always keeping
  the active tab visible so a filter can't orphan the on-screen panel; the guided demo clears
  the filter when it drives a tab. Refactored the 31 hand-written panel wrappers into one
  `TABS` map so tab/panel ids can't drift. New `.tabbar-row`/`.tab-filter*`/`.sr-only` CSS +
  `.tab:focus-visible`. Frontend-only, no endpoint/number touched. Green: `npx tsc --noEmit`
  clean, `npx next build` compiled (4/4 static, / = 67.3 kB, First Load 155 kB),
  `npx next lint` no warnings.

- 2026-08-13 — M36: first frontend test suite (SPEC §34 honesty guard).
  The frontend had zero automated tests — nothing pinned the behaviour of the pure helpers
  that render every headline number and back the editable-assumptions panel. Added a
  `frontend/tests/` suite with ZERO new dependencies, using Node 22's built-in `node:test`
  + `--experimental-strip-types` to run TypeScript directly (`npm test` →
  `node --test --experimental-strip-types tests/*.test.mts`). `format.test.mts` (8 tests)
  locks every `formatNumber` magnitude bucket incl. sign-preservation on negatives, and
  `formatSignedPct`'s sign rules — explicitly asserting the negative case renders a real
  U+2212 minus (not an ASCII hyphen) and that zero is unsigned. `dsl.test.mts` (6 tests)
  covers `getByPath` (nested / missing / non-object mid-path), `setByPath` and its
  immutability guarantee (original untouched, branch cloned, untouched branches independent),
  intermediate-object creation, non-object-intermediate replacement, and `fieldKind`'s
  type→control mapping. 14 tests, all green; no runtime code changed. `npx tsc --noEmit`,
  `npx next build` (/ = 67.3 kB, First Load 155 kB), and `npx next lint` all still clean.

- 2026-08-13 — M37: Minister's Brief export tab (`POST /brief`, SPEC §27/§37).
  The engine shipped `POST /brief` (+ `GET /brief/example`) after M36 — the one
  endpoint the UI hadn't surfaced, sibling of the North-Star answer. Added a
  `Brief` tab (right after North-Star) that renders the §37 answer as a
  self-contained Markdown memo. Input mirrors North-Star (compiled policy from the
  store, or a natural-language fallback that compiles first; horizon selector) plus
  an "include SIMULATED media section" toggle wired to `include_media`. On success:
  provenance banner + the endpoint's honesty `note`, a memo-meta card (title,
  echoed question, horizon, `policy_id`, `rendered from /north-star`, word count),
  the backend-supplied provenance key as tagged legend rows, an export toolbar
  (Copy Markdown via the Clipboard API with a graceful disabled state, Download
  `.md` via a Blob object-URL `ministers-brief-<policy_id>.md`), and the memo in a
  scrollable monospace block shown **verbatim** so no figure or provenance tag can
  be altered client-side. No new numeric model — the memo is a pure layout over
  `/north-star`, which reuses each deterministic layer verbatim, so it can never
  disagree with the tabs behind it (§34). Added `BriefRequest`/`BriefResponse`/
  `TagLegendEntry` + `runBrief()` to `lib/api.ts`; `idle`/`loading`/`error` states
  + retry that never mints a fabricated memo when the backend is down. Re-synced
  `frontend/README.md` (31→32 surfaces, new endpoint→SPEC row). `npx tsc --noEmit`,
  `npx next build` (/ = 68.7 kB, First Load 156 kB), and `npx next lint` all clean.

- 2026-08-13 — M38: Decision-under-uncertainty (Robustness) tab (`GET /robustness/objectives`
  + `POST /robustness`, SPEC §20/§21/§22). The engine shipped this decision layer after
  M37 declared the roadmap complete — one level above Stress: instead of "does *this*
  policy hold?", it compares *several candidate policies* across the baseline + every §20
  shock and reports which candidate each classic decision rule picks (nominal / maximin /
  minimax-regret-Savage / Laplace / most-robust). No new numeric model: every payoff is the
  same deterministic **Simulated** Δ(B−A) the Stress/Simulate endpoints return, so a
  candidate's numbers can't disagree with the tabs beside it (§34). Candidate slate = the
  compiled policy (un-amended) + user-toggleable transparent design variants (half/higher
  charge, transit-funded, general-fund, low-income exempt), each a compiled DSL via
  `applyAmendment` (the app's existing structured amendment loop) re-simulated by the
  backend — the UI invents no numbers. Renders: provenance tag, a headline banner that
  flags whether robustness **flips** the choice away from the nominal winner, a
  five-criterion decision-picks grid (each highlighting agree/differ vs the headline), a
  candidate scorecard (nominal/worst-case/mean payoff, max regret, robustness rate +
  holds/fails), a full regret matrix (candidates × states, per-state best=0 + row max-regret
  flagged, per-state confidence widening with horizon), and a collapsible method note.
  Objective + horizon selectors; `idle`/`loading`/`error` states + graceful objective-menu
  fallback; never mints a decision when the backend is down. Added `RobustnessReport`/
  `RobustnessCandidateScore`/`RobustnessStateResult`/`RobustnessDecisionPicks`/
  `RobustnessObjectives` types + `runRobustness()`/`fetchRobustnessObjectives()` to
  `lib/api.ts`; registered the tab right after Stress; re-synced `frontend/README.md`
  (32→33 surfaces, endpoint→SPEC row + prose). `npx tsc --noEmit`, `npx next build`
  (/ = 71 kB, First Load 159 kB), `npx next lint`, and `npm test` (14 pass) all clean.

- 2026-08-13 — M39: guarded the client-side city model, the biggest untested §34
  surface. Added `frontend/tests/cityModel.test.mts` (14 tests, +0 deps, auto-picked
  by the `tests/*.test.mts` glob) over `lib/cityModel.ts` + `lib/city.ts`: exact
  arithmetic for `cityConstants` (incl. empty-matrix zeros-not-NaN), `inflowByZone`,
  and `deltaPct` (zero/NaN/Infinity reference → `null`, no Infinity leak into a
  headline); plus `predict` invariants — year-0 shares = today's split (ramp 0),
  0–10 horizon clamped both ends, charge cuts CBD car share/CO₂ and lifts transit,
  public realm ramps slowly, baseline drifts up with growth, all outputs within
  documented bounds (support 0.05–0.95, congestion 0–1.6, shares 0–1, non-negative,
  finite) swept over every scenario × the horizon, and CO₂ = vehicle-km × the one
  published tailpipe factor. 28 tests total, all green. `npx tsc --noEmit`,
  `npx next lint` (clean), `npx next build` (/ = 71 kB, First Load 159 kB), and
  `npm test` (28 pass) all clean. No runtime code changed.

- 2026-08-13 — M40: guarded `applyAmendment` (lib/api.ts), the pure DSL transform
  behind the "apply amendment + re-simulate" loop (§29) and the Robustness candidate
  slate (M38). Added `frontend/tests/amendment.test.mts` (8 tests, +0 deps): input
  immutability, labelled-id slug, set_charge_amount replace, charge_multiplier 4-dp
  rounding, set-then-multiply compose order, case-insensitive exemption de-dup (fresh
  add + re-apply), revenue split summing to exactly 1, and bare-policy tolerance.
  36 tests total, all green. `npx tsc --noEmit` + `npx next lint` clean; no runtime
  code changed.

- 2026-08-13 — Verification checkpoint (no unchecked items remain). ROADMAP_UI.md is
  fully complete: all 54 items across M4–M40 checked. Confirmed every documented
  backend route (47 paths incl. /world, /citizen, /business, /robustness, /brief,
  /north-star, /sensitivity, /compare/grand, /assumptions*) has a UI surface in
  lib/api.ts — nothing new to expose. The one new engine commit since M40
  (LEZ modelled as a distinct mechanism, §7.5) is a numeric-model change on
  /simulate; it needs no UI change because PolicyCompiler is generic — it posts
  free text to /policy/compile and renders the returned DSL (incl. the
  low_emission_zone intervention type) through the editable-assumptions panel +
  raw-JSON view, with no hardcoded intervention-type list to update. Full green:
  `npx tsc --noEmit` (0), `npm test` (36 pass), `npx next lint` (clean),
  `npx next build` (/ = 71 kB, First Load 159 kB). No runtime code changed.

## 2026-08-13 — UI-track: M41 — example-policy gallery (one click per mechanism, SPEC §3/§7.5/§34)
The engine track had made three pricing families numerically distinct (cordon
charge vs. low-emission zone vs. workplace parking levy) plus pedestrianisation
and a transit-reinvested charge, but `PolicyCompiler` still shipped a single
hardcoded congestion-charge "Load demo policy" button — a judge had no way to
discover or one-click compare the mechanisms the engine works to tell apart.
Replaced it with an example-policy gallery: `EXAMPLE_POLICIES` (five curated
plain-language prompts, one per mechanism family; the §29 demo stays the default)
rendered as toggle chips, each with a mechanism tag + a "what to watch" note that
frames the *lever and the comparison to make*, never a predicted number (SPEC
§34). Clicking a chip loads its text and resets any compiled result to `idle` so
a prior policy's numbers can't linger under different text; a manual textarea edit
clears the active-chip highlight. Prompts grounded in the engine's documented
§7.5 mechanisms (verified against `ROADMAP_ENGINE.md`), so each compiles to a
real, distinct DSL — the UI mints nothing. Added `.example-gallery`/`.example-btn`
styles to `globals.css`. Full green: `npx tsc --noEmit` (0), `npm test` (36 pass),
`npx next lint` (clean), `npx next build` (/ = 72 kB, First Load 160 kB).

## 2026-08-13 — M42: gallery chips for the two new honest mechanisms (time-of-day pricing + standalone transit)
Engine commit f5852af made two more mechanisms numerically distinct that no UI surface exposed: (1) charge `active_hours` now scale the per-trip signal by overlap with the inbound AM peak (a late-starting cordon ≠ an all-day one — previously byte-identical, dishonest per §34); (2) a standalone `transit_investment` (no charge/ban) recovered as a real supply-side lever instead of a silent no-op. Added two chips to `PolicyCompiler`'s `EXAMPLE_POLICIES`:
- **Late-start charge** (mechanism *Time-of-day pricing*): the 12-credit cordon operating 8:30am–6pm; verified via the rule-based compiler to yield road_pricing with active_hours 08:30–18:00 → `_active_hours_coverage` 0.5 (half the AM peak). `watch` frames the timing→attenuation comparison vs the all-day cordon, no figure.
- **Fund buses, no charge** (mechanism *Transit supply*): pure carrot (fare cut + new routes + frequencies, general-fund, no charge/ban); verified to yield transit_investment DSL. `watch` frames the honest missing-stick guardrail (car drop ≤ transit gain) vs any pricing scheme.
Both prompts grounded in the engine's §7.5 mechanisms and compile to real, distinct DSL — the UI mints no numbers (§34). No new types/styles/endpoints; existing chip loader + active-highlight + idle-reset apply unchanged. `tsc --noEmit` + `next build` + `next lint` + `npm test` (36) all clean.
Follow-up: none. Frontend README has no example-count to sync (gallery is part of the compiler surface).

## 2026-08-13 — M43: active-travel reinvestment chip (SPEC §7.5/§9/§34)
Engine commit 61dd8ec made `revenue_allocation.active_travel` actually bite (an
`active_travel_speed_multiplier = 1 + share·0.20` scales active-travel speed + max
walk/cycle distance in World B, pulling nearest-margin short-trip commuters onto
foot/bike; engages only when the charge raises revenue, ramps over the horizon).
No gallery chip exposed it. Added one to `PolicyCompiler.EXAMPLE_POLICIES`:
- **Charge, fund cycling** (mechanism *Active-travel reinvest*): 12-credit cordon
  spending 80% of revenue on protected cycle lanes + wider pavements. Verified via
  `.venv/bin/python parse_policy` → road_pricing, `active_travel = 0.8`,
  `public_transport = 0.0` (transit is matched first, so no transit % is named).
  `watch` frames the revenue-destination comparison vs the bus-funded charge and the
  neutral-until-revenue guardrail (§9), no figure. Placed between "Bus-funded charge"
  and "Fund buses, no charge" so the three revenue-destination levers sit together.
Chip mints no numbers (§34); existing chip loader + active-highlight + idle-reset
apply unchanged; no new types/styles/endpoints. `tsc --noEmit` + `next build` +
`next lint` + `npm test` (36) all clean.
Follow-up: none. Frontend README has no example-count to sync (gallery lives inside the compiler surface).

## 2026-08-13 — M44: stated-equity-constraint compliance card (SPEC §7.3/§34)
Engine commits baf09f3/be16d16 made the microsim *test* a policy's own stated
`max_low_income_burden_increase_pct` cap against the modelled low-income-decile
charge burden, returning `constraint_check` on `MicrosimReport`. The frontend
neither typed nor rendered it — a policy could declare an equity cap and a judge
had no way to see whether the twin says it kept or broke that promise (SPEC §34:
a constraint you never test is theatre). Added `ConstraintCheck` +
`MicrosimReport.constraint_check` types and a pure `constraintVerdict` mapper
(zero burden → *moot*, in-cap real burden → *pass*, overshoot → hard *fail*,
never softened; trusts the engine's `satisfied` flag). `MicrosimPanel` now renders
a `ConstraintCheckCard` (✓/✕ glyph, verdict pill, cap-vs-modelled + signed
headroom/overshoot, the engine's verbatim note, provenance tag) between the
winners headline and the regressivity card — shown only when the field is present.
Added `.ms-constraint*` styles mirroring the regressivity card. New
`tests/microsim.test.mts` (5 tests). Card mints no numbers; all values are the
engine's. `tsc --noEmit` + `next build` + `next lint` + `npm test` (41) all clean.
Follow-up: none.

## 2026-08-13 — M45: gallery chips now apply the charge under the keyless fallback (SPEC §7.5/§29/§34)
While confirming M44's constraint card was reachable, found a latent demo bug in
the frontend-owned gallery prompts. With no LLM key (the env default), compilation
falls back to the rule-based parser, whose `_find_amount` doesn't recognise "12
credits" (only £/pounds/"charge of N"). Six of eight chips said "…12 credits to
enter…" → compiled to `amount=None` → zero-charge policy → all-zero microsim and a
hollow constraint card; the LEZ chip additionally mis-classified as road pricing
(its "charges…entering" hit the `charge.*enter` rule before the LEZ rule). M41–43
verified mechanism/coverage but never the amount, so it slipped through. Reworded
the six charge-bearing prompts to "Introduce a charge of 12 credits on private
vehicles entering…" (cordon variants) and "…a daily levy of 12 credits on …
non-compliant vehicles, in force between…" (LEZ, which now avoids the road-pricing
trigger). Verified all 8 end-to-end against the backend compiler + microsim:
6 now parse amount=12 with the intended distinct mechanism and nonzero payers
(92–1032); the 2 no-charge chips keep amount=None. Hours, exemptions, revenue
splits and the 5% cap all preserved; nothing invented. `tsc --noEmit` +
`next build` + `next lint` + `npm test` (41) all clean.
Follow-up: engine track may want `_find_amount` to recognise "N credits" so the
rule-based fallback is robust to natural phrasings (backend-owned; not editable
from this track).

## 2026-08-13 — M46: close the backend surface (GET /brief/example)
Audited the panel↔endpoint map: the UI already called every documented backend
endpoint except one — `GET /brief/example`. The Brief tab was the only
sample-bearing surface not exposing its zero-body example helper (Backtest,
Citizen, Business, Analogue all surface theirs), so a judge landing on it with no
compiled policy couldn't see the finished artifact. Added `getBriefExample()` to
`lib/api.ts` (same honest throw-on-error contract as `runBrief`) and a "Load
example brief" button to `BriefPanel` that renders the canonical §28 demo memo
body-lessly. An `isExample` flag stamps the result with an honest `example` chip
("the canonical §28 demo congestion charge — NOT the policy compiled above"),
distinguishes the loading label, and points the error-state Retry at the correct
path. Added `.brief-example-note` to `globals.css`; re-synced the README
endpoint→SPEC row (`POST /brief`, `GET /brief/example`) so "every documented
backend endpoint has a UI surface" is now literally true. No new numeric model.
`tsc --noEmit` + `next build` + `next lint` + `npm test` (41) all clean.

## 2026-08-13 — M47: surface the killer-demo example (GET /run/example)
After M46 closed the endpoint→surface map for `/brief/example`, the engine track
shipped two more zero-body example helpers (`GET /run/example`,
`GET /north-star/example`) that the UI didn't surface — reopening the gap M46
closed. Added `getRunExample()` to `lib/api.ts` (same honest throw-on-error
contract as `runScenario`) and a "Load example run" button to `RunPanel` that
orchestrates the canonical §28 demo pipeline body-lessly, so the §29
killer-demo narrative is visible with no compiled policy in the store. An
`isExample` flag stamps the result with an honest `example` chip ("the canonical
§28 demo congestion charge — NOT the policy compiled above"), distinguishes the
loading label, and points the error-state Retry at the correct path. Reused the
existing `.brief-example-note` style — no new numeric model, types, styles or
endpoints. Backend on this host's :8000 is a different service, so no live smoke
test; verified against the documented contract with the honest error path
covering the not-live case. `tsc --noEmit` + `next build` + `next lint` +
`npm test` (41) all clean.
Follow-up: M48 will do the same for `GET /north-star/example` on `NorthStarPanel`.

## 2026-08-13 — M48: surface the §37 answer example (GET /north-star/example)
Second half of the M47 fix. Added `getNorthStarExample()` to `lib/api.ts` (same
honest throw-on-error contract as `runNorthStar`) and a "Load example answer"
button to `NorthStarPanel` that composes the canonical §28 demo §37 answer
body-lessly, so the North-Star tab — the flagship URBAN experience — is usable
with no compiled policy in the store. An `isExample` flag stamps the result with
an honest `example` chip ("the canonical §28 demo congestion charge — NOT the
policy compiled above"), distinguishes the loading label, and points the
error-state Retry at the correct path. Reused the existing `.brief-example-note`
style — no new numeric model, types, styles or endpoints. With this, every
zero-body backend example helper (/brief, /run, /north-star, /backtest) has a
one-click UI surface again. `tsc --noEmit` + `next build` + `next lint` +
`npm test` (41) all clean.
Follow-up: re-synced `frontend/README.md`'s endpoint→SPEC table — the North-Star
row now lists `GET /north-star/example` and the Run row `GET /run/example`
(mirroring how the Brief/Backtest rows already list their example helpers), so
the "every documented backend endpoint has a UI surface" claim is literally true
again. Audited backend routes vs `lib/api.ts` fetches: no other unsurfaced
endpoint remains.

## 2026-08-13 — M49: surface GET /compare/example on the Grand-counterfactual tab
The engine track had shipped `GET /compare/example` (its M49) but the UI never
surfaced it. Added `getCompareExample()` to `lib/api.ts` (body-less GET, same
throw-on-error contract as `runGrandCompare`) and wired a "Load example
comparison" button into `GrandComparePanel`. Un-gated the panel from `!policy`:
the horizon / World-D-target selectors and the "Compose A/B/C/D" button now
*disable* rather than disappear when no policy is compiled, so the example
quartet is always one click away for a judge landing cold. An `isExample` flag
stamps the result with an honest `example` chip (from `/compare/example`, **not**
the policy above) and a fresh compiled policy clears it. Reused existing
`.brief-example-note` + `.grand-controls` CSS — no new numeric model, types, or
endpoints; the button mints no numbers. `tsc --noEmit`, `next lint` (0), `npm
test` (41 pass), and `next build` all clean. This closes the endpoint→surface
map for every keyless example helper the engine shipped: `/brief`, `/run`,
`/north-star`, `/backtest`, `/compare` each now have a one-click UI surface.

## 2026-08-13 — M50: surface the keyless §26 causal trace (GET /evidence/example)
Added `getEvidenceExample()` (`GET /evidence/example`) to `lib/api.ts` with the
same throw-on-error contract as `runEvidence`, and taught `EvidenceDrawer` an
`example` mode (policy/metricKey now optional). In example mode the drawer fetches
the body-less keyless GET — the engine's M51 sibling of `POST /evidence`, tracing
the canonical §26 peak-transit metric ("why does public transport demand rise?")
on the §28 demo congestion charge — and shows a `.brief-example-note` chip
stamping it "**not** a policy you compiled". Wired an always-available "Example
evidence trace ▸" button into the Outcomes `dashboard-head` (ungated on policy),
rendered by `TwinWorkspace` via a dedicated `exampleTrace` flag kept separate from
the policy-driven `explainKey`. Before this, the Evidence Drawer was reachable
only via a metric tile's "Evidence ▸" button, which appears only once a policy is
compiled — so a judge landing cold couldn't open the causal ladder at all. This
closes the endpoint→surface map for the last keyless example helper: `/brief`,
`/run`, `/north-star`, `/backtest`, `/compare`, and now `/evidence` each have a
one-click keyless UI surface. No numbers minted (trace copied from the
deterministic sim, no LLM on the numeric path). `tsc --noEmit`, `next lint`,
`next build`, and `npm test` (41 pass) all clean. Note: the backend instance
running on :8000 is stale (returns 404 for `/evidence/example`); the UI degrades
to an honest "Evidence unavailable" state until the engine deploy catches up.
