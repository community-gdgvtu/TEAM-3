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

## M18 — Surface the spatial traffic-assignment layer (SPEC §7.7)
The engine shipped `POST /spatial` — a peak-hour static user-equilibrium assignment
(MSA + BPR) that loads the driving subset of the deterministic mode-choice agents onto
the real Meridia road grid — after M17. Same rules: every number tagged, displacement
visible (A vs B), never invent one when the backend is down.
- [x] Spatial tab: `POST /spatial` → where the policy's traffic goes. Render a headline strip (peak-hour car trips A→B, cordon-inflow Δ%, network vehicle-hours Δ% with good/bad colouring); World A (baseline) vs World B (policy) network-state cards (vehicle-hours/-km, mean speed, mean/max v/c, congested + overcapacity arcs, cordon inflow); a notable-link-loads table (flow A→B with signed Δ, colour-coded v/c pills, congested speed, cordon-crossing chip) plus separate over-capacity bottleneck lists for B and A; job-accessibility (gravity mean A→B + population-weighted Δ%, top gainer/loser zones); and a road-CO₂ dispersion proxy (CBD + network totals A→B, biggest drops vs biggest rises = displacement, displacement note). All Simulated (deterministic assignment, no LLM); auditable `params` + explicit `not_modelled`; honest `waiting`/`idle`/`error` states when the backend is down (SPEC §7.7/§34)

## M19 — Surface the reproducibility manifest (SPEC §32)
The engine shipped `POST /reproduce` — the machine-readable record behind SPEC §32's
"REPRODUCE RUN" affordance — after M18 declared the roadmap complete. Same rules: every
value tagged, never invent one when the backend is down; this manifest is Observed *about*
the run, not a simulation output.
- [x] Reproduce tab: `POST /reproduce` → the content-addressed run manifest. Render the headline reproduction key (`run_id` with copy-to-clipboard, a *proven* reproducible ✓/✗ badge from the backend's twice-run digest comparison, `output_digest`, code version, app version, seed, timestamp); a "how to reproduce" note; a prominent SPEC §34 honesty line asserting no LLM prompt entered the numeric path (`prompts` empty) and no pinned model reports LLM-touched numbers; content-addressed dataset versions (name, kind, path, seed, `sha256`, with a `MISSING` guard); model versions pinned to code (determinism + numbers-are-model-only badge + spec sections + output tag); and a collapsible pinned-assumption table (label / value / source / tag). The manifest is Observed about the run; deterministic, no LLM. Honest `idle`/`waiting`/`error` states when the backend is down — never mints a fake key (SPEC §32/§34)

## M20 — Surface the stress-testing environment (SPEC §20)
The engine shipped `POST /stress-test` + `GET /stress-test/catalogue` after M19 — the
external-shock stress-testing environment SPEC §20 asks for (does the policy fail under a
recession + fuel shock?). Same rules: every number tagged, uncertainty/fidelity visible,
never invent one when the backend is down.
- [x] Stress tab: `GET /stress-test/catalogue` → toggleable shock chips (recession, fuel-price spike, flood, heatwave, population growth, migration change, technology adoption, interest-rate shock) each showing its model `fidelity` (modelled/partial/proxy); `POST /stress-test` (with horizon selector) → a robustness roll-up banner (holds/degrades/fails counts + keys, headline), a no-shock baseline reference card, and a per-scenario card each with a verdict pill (holds/degrades/fails), horizon-aware confidence + fidelity badges, the plain-language `caveat`, a per-headline-metric stress table (Δ no-shock → Δ shocked with %, a retained-benefit bar with a 100%-of-baseline marker, per-metric verdict robust/weakened/neutralised/reversed), and the exact auditable `overrides`. Each shock is a transparent scenario assumption applied to BOTH worlds so Δ(B−A) still isolates the policy; policy deltas Simulated (deterministic, no LLM), shock magnitudes Estimated — both provenance classes surfaced; `idle`/`waiting`/`error` states when the backend is down, never fabricates a robustness claim (SPEC §20/§34)

## M21 — Surface the historical-analogue / causal layer (SPEC §7.1/§8)
The engine shipped `POST /analogues` (+ `GET /analogues/cases`) after M20 declared the
roadmap complete — the causal-inference layer SPEC §7.1 asks for, estimating the flagship
cordon effect from *comparable real-world schemes* instead of the synthetic-city model.
Same rules: every number tagged, band visible, never invent one when the backend is down.
- [x] Analogue tab: `POST /analogues` → the flagship cordon effect read from eight real schemes (London, Stockholm, Singapore, Milan, Gothenburg, Oslo, Ghent, Madrid) via a difference-in-differences transfer. Render the transfer-weighted central estimate + confidence band (widens when analogues are weak/disagree), an `analogue_quality` (strong/moderate/weak) + transferability pill; a DiD range chart plotting each pooled scheme's effect (marker opacity = pool weight) against the highlighted pooled CI + central line; the **structural cross-check** card (agent-based `structural_effect_pct` Simulated vs analogue `analogue_effect_pct` Estimated + signed gap + agreement pill consistent/moderate-gap/large-gap + interpretation — the SPEC §8 "real cordons rarely exceed ~30%" sanity floor); a contributing-cases table (DiD effect, identification strength, transferability, pool weight; context-only schemes shown greyed at weight 0); the `identification_diagnostics` (parallel-trend caveats) and collapsible `not_modelled` list. Historical outcomes Observed but illustrative, the transfer Estimated — both provenance classes surfaced; a "no comparable scheme" honest state for transit-only/other policies; `idle`/`waiting`/`error` states when the backend is down, never mints a fake estimate (SPEC §7.1/§8/§34)

## M22 — Surface the time-series forecast layer (SPEC §7.2)
The engine shipped `POST /timeseries` after M21 declared the roadmap complete — the
statistical time-series layer SPEC §7.2 asks for, which fits **World A first** with a
structural model, then lets the deterministic policy Δ alter that baseline trajectory.
Same rules: every number tagged, uncertainty visible (and it must *widen with horizon*),
never invent one when the backend is down.
- [x] Time-series tab: `POST /timeseries` → the fitted structural forecast. For each headline metric render a per-metric selector and a chart overlaying the seeded **synthetic monthly history** (Simulated, muted line on the negative-time axis) with the **World A** baseline forecast (Estimated; local-linear-trend + 12-month seasonal + AR(1)) and the **World B** policy trajectory (Simulated; World A altered by the ABM Δ(B−A)), each drawn as nested 80%/95% prediction bands that visibly *widen toward year 10* plus a central line, split by a "now → forecast" divider; a headline strip (World A vs World B central at the final horizon with their 80% bands + the signed policy shift Δ(B−A)%); an auditable fit-diagnostics grid (level, trend/month, seasonal amplitude, AR(1) φ, residual σ, in-sample MAPE + honest held-out MAPE, method string); a per-horizon policy-shift row; and a collapsible model-assumptions table + the `not_modelled` scope-limit list. Three provenance classes on one chart — history Simulated, statistical baseline Estimated, policy shift Simulated — all surfaced; no LLM on the numeric path; `idle`/`waiting`/`error` states when the backend is down, never mints a fabricated trajectory (SPEC §7.2/§8/§34)
