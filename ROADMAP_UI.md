# ROADMAP — UI track (frontend)

**This track owns ONLY:** `frontend/**` and this file + `PROGRESS_ui.md`.
**Never edit** `backend/**`, `data/**`, `scripts/**`, `ROADMAP_ENGINE.md`, `PROGRESS_engine.md`,
`README.md`, `ROADMAP.md`, `SPEC.md`, `AGENT_LOOP.md`. This keeps parallel tracks from colliding
on git. Lock file: `.lock-ui`.

Work top-to-bottom. Each run, do as many items as you can finish cleanly (commit+push after
**each** item). Keep `next build` + `tsc --noEmit` clean at every commit. You may build ahead of
the backend: call the documented endpoints (`/health`, `/baseline`, `/policy/compile`, and the
coming `/simulate`, `/parliament/debate`, `/media`), and when an endpoint isn't live yet, show a
clear "waiting for backend" state — never invent fake numbers and present them as real (SPEC §34).
Mark any generated media in the UI as SIMULATED. Uncertainty bands must be visible.

## M4 — 3D map + time machine UI (the visual centerpiece, SPEC §17/§27)
- [x] Install + render MapLibre GL + deck.gl. Draw the Meridia city from `/baseline` data (or a new `/city` endpoint if present): zones (choropleth), roads, the CBD cordon polygon
- [x] deck.gl layers for traffic flow, transit demand, and a support/opposition heatmap (driven by sim results when available; placeholder-but-clearly-labelled otherwise)
- [x] Draggable timeline scrubber (T0→10y checkpoints) that drives the map + dashboard state
- [x] Dashboard tiles: Traffic, CO₂, Transit, Equity burden, Support — each showing value + Δ vs baseline + a visible uncertainty band; tag each with its provenance class

## M5 — Parliament view + amendment loop (SPEC §11/§27)
- [x] Parliament screen: list the agents (Government/Opposition/Equity/Economist/Devil's Advocate) and render `/parliament/debate` transcript with citations
- [x] "Apply amendment + re-simulate" button → calls `/simulate` with amended DSL and updates the map/dashboard (the killer interaction, SPEC §29)
- [x] Failure Mode Register panel from the Devil's Advocate output

## M6 — Public reaction + media (SPEC §13/§15)
- [x] Public reaction view: cohort support distribution by income/geography (charts). Use the `dataviz` conventions
- [x] Simulated press feed: archetype headlines at Month 5 and Year 2, each visibly stamped SIMULATED

## M7 — Evidence drawer + polish (SPEC §26/§27)
- [x] Click any dashboard metric → evidence drawer showing the provenance trace, assumptions, confidence (from the backend evidence endpoint)
- [x] Assemble the main screen layout per SPEC §27 (3D world + outcomes panel + timeline + [Parliament][Public][Press][Red Team] tabs) and wire the 60-second demo flow (SPEC §29)
- [x] Visual polish: consistent theme, loading/empty/error states, mobile-safe

## M8 — Surface the newer engine layers (SPEC §23/§14/§25)
The engine track has shipped analysis endpoints the UI hasn't exposed yet. Add a
tab per layer; keep every number tagged and never invent one when the backend is down.
- [x] SDG alignment tab: `POST /sdg` → per-goal indicator table (baseline/scenario/change/confidence, direction-aware improved/worsened), count-based headline (SPEC §23 forbids a composite score)
- [x] Opinion-diffusion tab: `POST /diffusion` → opinion trajectories over rounds, salience + polarisation, coalitions, dominant narrative; rounds labelled as information steps (NOT the Time-Machine horizon)
- [x] Backtest scorecard tab: `GET /backtest/example` + `POST /backtest` → forecast-vs-actual scorecard with error metrics; actuals stamped synthetic-benchmark

## M9 — Surface the transparency + ensemble engine layers (SPEC §8/§33/§18)
The engine track shipped more endpoints the UI still doesn't expose. Same rules:
every number tagged, uncertainty visible, never invent one when the backend is down.
- [x] Ensemble forecast tab: `POST /ensemble` → the flagship cordon effect estimated by 3 independent methods (agent-based / historical-analogue / elasticity) with per-method ranges, documented weights, and a disagreement band; band = method disagreement, not false precision (SPEC §8)
- [x] Model registry / transparency tab: `GET /registry` → the "how do we know this isn't AI astrology" manifest: model cards (method, determinism, LLM-role, output tag), data sources, live assumption index, and the SPEC §34 guardrail checklist with pass/fail (SPEC §33)
- [x] Institutional review tab: `POST /institutions` → multi-agent institutional feasibility/legal/fiscal review with per-institution verdicts (SPEC §18)

## M10 — Remaining engine endpoints the UI still doesn't expose (SPEC §16/§21/§22/§24)
Same rules: every number tagged, uncertainty visible, generated media SIMULATED,
never invent one when the backend is down. Endpoint paths as documented.
- [x] Press conference tab: `POST /press-conference` → spokesperson opening + 5 archetype journalist exchanges, each grounded in a Δ metric/event; whole thing stamped SIMULATED (fictional outlets), prose Generated over Simulated figures (SPEC §16)
- [x] Counterfactual compare tab: `POST /compare` → World A (baseline) vs B (intervention) vs amendment worlds C/D…, headline table of every world + Δ per metric at one horizon; baseline always present (SPEC §21)
- [x] Uncertainty fan tab: `POST /uncertainty` → Monte-Carlo median + 50/80/95% bands per horizon for a chosen metric, ranked most-influential assumptions, behavioural-regime disagreement (SPEC §24)
- [x] Policy optimiser tab: `POST /optimise` → objective + constraints → feasible Pareto frontier + representative picks (cheapest / most equitable / largest emissions cut / best balanced); outcomes Simulated, budget proxy Estimated (SPEC §22)

## M11 — Demo & presentation polish (SPEC §29)
Every documented engine endpoint now has a UI surface. This milestone makes the
whole thing legible to a judge in 60 seconds without inventing any numbers.
- [x] Guided demo tour: a floating launcher runs a spotlight walkthrough of the real UI — draft → compile → run counterfactual → scrub time → read tagged outcomes → Parliament debate/amendment → Red Team → transparency Registry. Pure guidance (never renders/fabricates a metric); drives the analysis tab bar; keyboard + Esc nav (SPEC §29)

## M12 — Demo resilience (crash safety, SPEC §34)
Every endpoint is now surfaced and every panel handles its own fetch idle/loading/error
states. This milestone hardens against the failure the per-panel states can't catch — a
render throw that would blank the whole app mid-demo — keeping the honesty contract intact.
- [x] App Router error boundaries: `app/error.tsx` (segment) + `app/global-error.tsx` (root layout). A render throw — unexpected backend payload shape, deck.gl/MapLibre runtime error, deep null deref — is contained to a themed, honest recovery card (clear message + error digest + Try again / Reload) instead of Next's default crash page. Never fabricates or estimates a metric; global-error is self-contained (own html/body, inline styles) since it replaces the root layout (SPEC §34)
- [x] Themed 404: `app/not-found.tsx` — a bad URL lands on an on-brand page with a route back to the twin instead of Next's bare default 404, completing error-surface coverage alongside the boundaries. Static, no data, no metrics
