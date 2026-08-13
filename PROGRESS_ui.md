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
