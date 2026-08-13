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
