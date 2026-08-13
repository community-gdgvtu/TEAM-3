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
