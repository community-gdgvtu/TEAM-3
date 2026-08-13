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

## M13 — Judge-facing frontend docs (SPEC §33/§34)
Every endpoint is surfaced and the app is crash-safe. The remaining gap is legibility for
a reviewer reading the repo (not the running app): the frontend README covers run/config
but not the panel↔endpoint↔SPEC map or *how* the honesty contract is implemented in the UI —
the single most judge-relevant thing about this track ("how do we know this isn't AI astrology").
Docs only; no fabricated numbers; accurately reflects the real code.
- [x] Expand `frontend/README.md`: architecture overview (App Router pages, `lib/api.ts` typed client, panel components), the full analysis-tab → endpoint → SPEC-section map (all 18 endpoints), and a "Honesty contract in the UI" section documenting the `MetricTag` provenance chips (`.tag.observed/.estimated/.simulated/.generated`), visible uncertainty bands, SIMULATED media stamps, "waiting for backend" states, and the crash-safe error boundaries (SPEC §34)

## M14 — Surface the economic spillover layer (SPEC §7.4)
The engine track shipped `POST /economy` after the UI roadmap was declared complete.
Same rules: every number tagged, uncertainty visible, never invent one when the backend
is down; be explicit about what the layer does *not* model (honesty surface).
- [x] Economy tab: `POST /economy` → the policy's local-economy spillover. Show the net partial-equilibrium annual impact with its band, each transparent transmission channel (mechanism, the Simulated physical driver it reads, elasticity/IO assumption, banded monetary estimate, direction, confidence), per-sector exposure (direction/magnitude, not fabricated hard jobs numbers), the `not_modelled` list and translation `assumptions`. Physical drivers Simulated, monetary translation Estimated — surface both provenance classes; partial-equilibrium caveat prominent (SPEC §7.4/§8/§34)

## M15 — Surface the recursive feedback layer (SPEC §7.6/§19)
The engine track shipped `POST /dynamics` — the stocks-and-flows loop SPEC §19 calls
"central to the concept" — after M14 declared the roadmap complete. Same rules: every
number tagged, uncertainty visible, never invent one when the backend is down.
- [x] Dynamics tab: `POST /dynamics` → the recursive feedback loop (charge → mode shift → revenue → transit capacity, and negative support → endogenous amendment → weaker charge → renewed crowding). Render the instantiated §19 cascade, the coupled monthly stock trajectories over 10y (demand vs capacity, crowding, charge, support) as banded SVG charts whose band widens with falling confidence, the closed-loop (political response ON) vs open-loop (OFF) end-state contrast with a toggle, the second-order feedback events with their causal chains, final-state tiles, the `not_modelled` list, and collapsible Simulated structural anchors + Estimated dynamics assumptions. Trajectory deterministic/LLM-free → Simulated; couplings Estimated — both provenance classes surfaced; `waiting`/`idle`/`error` states when the backend is down (SPEC §7.6/§19/§34)

## M16 — Surface the isolated amendment effect (SPEC §12)
The engine exposes a dedicated `POST /simulate/amend` that re-simulates the original
AND amended policies over the same baseline and returns the isolated **Δ(amended −
original)** — the amendment's own marginal effect. The Parliament amendment loop only
drove the map with the amended World B (`/simulate`), so the chamber never saw what the
amendment *itself* changed. Same rules: every number tagged, band visible, never invent.
- [x] Parliament amendment loop: on "Apply + re-simulate", also call `POST /simulate/amend` and render an "Amendment effect vs original policy" table — the concrete structured `changes` + the isolated `amendment_delta` per metric at the final checkpoint (signed Δ, %, and low…high band), a near-zero row shown as "≈ 0 (no change)". Distinct from the dashboard (amended-vs-baseline): here the "before" is the *original policy*. Deterministic/LLM-free → Simulated; runs alongside the existing map-driving `/simulate` call; honest error state when the backend is down (SPEC §12/§34)

## M17 — Surface the distributional microsimulation (SPEC §7.3)
The engine shipped `POST /microsim` after M16 declared the roadmap complete — the
person-level "who gains, who loses, by how much" layer SPEC §7.3 asks for directly.
Same rules: every number tagged, uncertainty/limits visible, never invent one when the
backend is down.
- [x] Microsim tab: `POST /microsim` → the policy's distribution. Render the winners/losers/unaffected split (count + share bar) with the population mean per-trip generalized-cost change and named biggest-winner / worst-hit groups; a prominent **charge-burden regressivity** card (ratio + verdict progressive/flat/regressive, payer count, mean payer burden); and four breakdown tables — by income decile (with burden-%-of-income column), household type, home neighbourhood, occupation — each row showing Δ generalized cost (with a scaled bar), daily money-equivalent, and the better/worse split. Welfare deterministic/LLM-free → Simulated; money-equivalent → Estimated (documented value-of-time) — both provenance classes surfaced; `not_modelled` list + auditable `params`; `waiting`/`idle`/`error` states when the backend is down (SPEC §7.3/§34)
