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

## M23 — Surface the data-fabric provenance layer (SPEC §4)
The engine shipped `GET /data-fabric` after M22 declared the roadmap complete — the
dataset ingestion & provenance layer SPEC §4 asks for: the dataset-level answer to
"where did every number ultimately come from?", complementing the metric-level
`/evidence` trace (§26), the model catalogue `/registry` (§33) and the per-run
`/reproduce` envelope (§32). Same rules: every dataset tagged, Meridia's synthetic
nature explicit, never invent a catalogue when the backend is down.
- [x] Data Fabric tab: `GET /data-fabric` → the dataset catalogue. Render the §4 `input data → transformation → model → assumptions → result` lineage contract, a summary-counts strip (datasets/synthetic/assumption-sets/records/native-formats/harmonisation-implemented — all read live off disk), and a collapsible card per dataset carrying the full §4 provenance record: publisher + source, an auditable file-facts grid (format, record count, missingness, the content-hash `revision`, scope/resolution/frequency/period/units/license — all computed live from the file bytes so they can't drift from what runs), a confidence line, the variable list (name/type/description/missing-%), the ordered transformation history (each step tagged), and the real-world analogues shown as *schema-compatible with (not a live source)* to keep the synthetic-city honesty; plus the supported-ingestion-format contract (native/adapter-ready/declared chips) and the harmonisation-pipeline stages (implemented ✓ / declared ○ + code path). The manifest is Observed *about* the data on disk; datasets themselves Simulated/assumption-set; deterministic, no LLM. Honest `idle`/`loading`/`error` states when the backend is down — never mints a fake dataset record (SPEC §4/§34)

## M24 — Surface the scenario orchestrator (SPEC §28/§29 — the killer demo)
The engine shipped `POST /run` after M23 declared the roadmap complete — the one
endpoint the UI hadn't surfaced. It composes the whole engine (compile → simulate
→ public → parliament → amendment re-simulation → media) into a single,
mutually-consistent payload, reusing existing deterministic layers so the
dashboard, parliament, amendment and media can never disagree. The per-layer tabs
already exist; this tab's distinct value is proving that *consistency* in one call.
Same rules: every number tagged, uncertainty visible, generated media SIMULATED,
never invent one when the backend is down.
- [x] Run tab: `POST /run` → the §29 killer demo in one call. Drive it from the compiled policy in the store (or a natural-language fallback box so the tab runs compile→pipeline standalone) with a Time-Machine horizon selector; render a consistency banner (one call / one simulation, numbers Simulated · prose Generated · no LLM in the numeric path), the ordered §29 narrative beats (timecode → stage → response section → grounded one-liner), the composed outcomes dashboard at the chosen horizon (per-metric World A→B, signed Δ + %, uncertainty band, provenance chip, good/bad colouring by metric), a net-public-support gauge, a parliament snapshot (motion + tally pills + summary, cross-linked to the Parliament tab), the amendment block (source pill + rationale + the isolated Δ(amended − original) table at the final checkpoint, ≈0 rows shown as "no change"), and a SIMULATED-stamped press snapshot (fictional outlets + disclaimer). No new numeric model — every section reads the same compiled policy and the same run; `idle`/`loading`/`error` states when the backend is down, never fabricates a narrative (SPEC §28/§29/§34)

## M25 — Surface the change-assumptions-and-rerun layer (SPEC §34.10)
The engine shipped `GET /assumptions` + `POST /assumptions/rerun` after M24
declared the roadmap complete — the last endpoint the UI hadn't surfaced, and
SPEC §34's tenth product guardrail ("users can change the model's input
assumptions and re-run"). The §24 uncertainty fan already *sweeps* these knobs
and ranks the most-influential one, but nothing let a user pin an assumption to
a chosen value and re-run the deterministic core to watch the headline move.
The overridable catalogue is the *same* `ASSUMPTIONS` registry the uncertainty
engine sweeps (single source of truth), so the two can never drift. Same rules:
inputs Estimated, outputs Simulated, no LLM on the numeric path, honest clamp +
`waiting`/`idle`/`error` states, never fabricate a contrast when the backend is down.
- [x] Assumptions tab: `GET /assumptions` → the overridable-knob catalogue (live from the code: label, target model, plausible [low, high] range, live default, unit) rendered as per-assumption sliders that pin off their default; a Time-Machine contrast-horizon selector (Y1/Y2/Y5/Y10); `POST /assumptions/rerun` → re-runs the exact deterministic World-A/World-B/Δ pipeline `/simulate` uses with the pinned overrides and renders (a) an applied-overrides list echoing default → applied with an honest **clamped-to-range** flag when a request fell outside the documented band (SPEC §34), and (b) a per-metric contrast table showing Δ(B−A) under default assumptions vs the overridden run, the signed shift (effect of the user's change) with a scaled bar + %-of-default, good/bad-coloured by metric direction, ≈0 rows shown as "no change". The overridable set is the same one the §24 uncertainty engine sweeps so the two never disagree; inputs Estimated, the re-run Simulated (deterministic, no LLM); `idle` (no policy) / `loading` / catalogue-`waiting` / `error` states when the backend is down, never mints a fabricated contrast (SPEC §34.10/§34)

## M26 — Surface the grand counterfactual A/B/C/D (SPEC §21/§22)
The engine shipped `POST /compare/grand` after M25 declared the roadmap complete —
the canonical §21 four-way comparison the plain `/compare` never composed. Where
`/compare` takes arbitrary caller amendments, this one names the quartet by role
(A baseline / B policy / C opposition amendment / D URBAN-optimised), auto-derives
World C, wires the §22 optimiser in as World D, and returns a `derivation` audit of
how C/D were composed. Same rules: every number tagged, baseline always present,
never invent one when the backend is down.
- [x] Grand tab: `POST /compare/grand` → the canonical A/B/C/D comparison. Drive it from the compiled policy with a Time-Machine horizon selector and a World-D optimiser-target selector (best-balanced / cut-emissions / protect-low-income, each a transparent objective+constraints pair). Render a consistency banner (one deterministic model, four worlds; C/D re-simulated through the same path as B; no new numeric model, no LLM), role-coloured A/B/C/D world chips, the headline table (baseline + each world's value + Δ-vs-baseline per metric at the horizon), and the **derivation audit**: World C card (amendment source caller/auto-derived + structured edits + rationale, or an honest "no amendment applies" state) and World D card (which optimiser recommendation slot was picked, objective/constraints, feasibility + candidate counts, and the chosen config re-expressed as concrete policy edits). Every world Simulated (deterministic, re-simulated identically to B), amendment/optimiser inputs Estimated — both surfaced; `idle`/`loading`/`error` states when the backend is down, never fabricates a comparison (SPEC §21/§22/§34)

## M27 — Surface the Baseline World Model (SPEC §5/§28.2)

The engine now composes World A into the six SPEC §5 layers via `GET /world` — the
browsable digital twin the §28.2 demo renders (roads, transit, population cohorts,
businesses). The UI had no tab for it. This is the structural "here is the world
before any policy" view every other tab implicitly runs against.

- [x] World tab: `GET /world` → the browsable Baseline World Model (World A), the digital twin the demo renders (SPEC §28.2). Policy-independent, loads on mount. Render a topline (World-A chip + composition provenance + layer count), the note, and a collapsible SPEC §5 smallest-sufficient layer-selection rationale; then a card per layer, each carrying its own provenance chip and honest collapsible `not_modelled` list: **Population** (agent/CBD-commuter/income/age/mobility stat grid + income-band/age-band/household-size/occupation share bars + Estimated behavioural priors), **Economy** (city vs CBD jobs + share, employment-by-sector bars, mean-wage-by-band bars), **Geography** (zones/roads/cordon-links/network-capacity/buildings/commercial-zones/transit stat grid + land-use/road-class/building-type bars), **Environment** (commuter-CO₂ daily/annual/intensity + green-space + water-layer presence + land-use bars), **Institutions** (Observed description of the modelled Parliament §11 + institutional-reviewer §18 agents as chips), and **Society** (Estimated per-income-band opinion priors on a −1…+1 axis, media-environment chips §15, and civic-actor cards with signed priors + rationale §14). Structural counts read from the synthetic Meridia dataset / baseline ABM — Simulated; institutions Observed, society priors Estimated — all three provenance classes surfaced on one screen; not a forecast, no LLM on any number (SPEC §34); `idle`/`loading`/`error` states when the backend is down, never mints a fabricated city (SPEC §5/§28.2/§34)

## M28 — Complete the SPEC §29 guided demo through the killer tabs (SPEC §28/§29/§32)
The guided demo tour (the judge's 60-second walkthrough) was written before the
newest flagship tabs shipped, so it stopped at Registry and never showed **Run**
(M24 — the whole pipeline composed into one mutually-consistent call, SPEC §28/§29)
or **Reproduce** (M19 — the content-addressed run receipt, SPEC §32). A judge
following the guided path never reached the strongest honesty beats. Pure guidance,
no invented numbers — the tour points at what the backend produced (or its honest
`waiting` state) and explains it.
- [x] Extend the guided tour (`lib/demo.ts`): add a **Run** step ("the whole pipeline in one call" — compile → simulate → public → parliament → amendment → press, all reading one simulation so the dashboard/tally/amendment-Δ/SIMULATED press can't disagree; numbers Simulated, prose Generated, no LLM on the numeric path) after Red Team, and a closing **Reproduce** step ("the content-addressed receipt" — run id, output digest, pinned code/data/seeds, proven-reproducible badge from the backend's twice-run digest diff) as the finale; widen `DemoTab` with `run`/`reproduce` (both already `PanelTabs` TabKeys, so tab-switching is type-safe), renumber the captions, and keep the generic `DemoTour` renderer/`[data-tour="tabs"]` anchor untouched. The tour still never renders a metric (SPEC §34); `tsc --noEmit` + `next build` clean (SPEC §28/§29/§32/§34)

## M29 — Surface the North-Star answer (SPEC §37 — *the* URBAN experience)
The engine shipped `POST /north-star` after M28 declared the roadmap complete —
the one endpoint the UI hadn't surfaced, and the SPEC §37 flagship: a minister
asks "What happens if we implement this?" and URBAN answers with a fixed, ordered
15-line narrative (baseline → analogues → mechanisms → median outcome →
uncertainty → winners → losers → failure modes → the opposition's strongest
argument → opinion evolution → media narratives → three risk-reducing amendments
→ each amendment's effect → the best-fit configuration → every assumption). It
introduces **no new numeric model** — every section embeds the *same*
deterministic layer output the standalone endpoints return, so the answer can
never disagree with the deep tabs. Same rules: every number tagged, uncertainty
visible, generated media SIMULATED, never invent one when the backend is down.
- [x] North-Star tab: `POST /north-star` → the fixed §37 minister's answer. Drive it from the compiled policy in the store (or a natural-language fallback box so the tab runs compile→answer standalone) with a Time-Machine horizon selector. Render a provenance banner (Simulated numbers · Estimated transfers · Generated prose · no LLM in the numeric path), the minister's-question echo (with horizon + policy id), the **ordered §37 narrative** — one row per §37 line carrying the question, the deterministic one-sentence synthesis read straight from the numbers, a provenance chip (Simulated/Estimated/Observed/Generated), the `backs` field it reads and a cross-link to the deep tab that carries the full evidence — the composed median-outcome dashboard at the chosen horizon (per-metric World A→B, signed Δ + %, uncertainty band, provenance chip, good/bad colouring), the risk-reducing amendment cards (label + targeted risk + rationale + the isolated Δ(amended − original) table at the final checkpoint, ≈0 rows shown as "no change"), and the §37.15 assumptions/guardrail footer (documented-assumption + data-source counts, the SPEC §34 guardrail pass/fail tally, the explicit "no LLM produces any figure" honesty line, and the guardrail checklist). No new numeric model — every section reads the same compiled policy and the same run, reusing the existing typed `lib/api.ts` backing types (AnalogueEstimate, UncertaintyResult, MicrosimReport, FailureModeRegister, DebateResponse, DiffusionResult, MediaResponse, OptimiserResult, AmendmentComparison, …); `idle`/`loading`/`error` states when the backend is down, never fabricates a narrative (SPEC §37/§34)
- [x] Make the North-Star the guided-tour capstone: widen `DemoTab` with `northstar` (already a `PanelTabs` TabKey → type-safe), add a closing step 10 after Reproduce that spotlights the North-Star tab and frames it as the §37 culmination — every layer the judge just saw fused into the single ordered answer to "What happens if we implement this?", with nothing new computed so it can't disagree with the tabs behind it. Pure guidance, renders no metric (SPEC §34); `tsc --noEmit` + `next build` clean (SPEC §29/§37)

## M30 — Re-sync the frontend README with the shipped 28-tab surface (SPEC §34)
The `frontend/README.md` "Analysis surfaces → endpoint → SPEC" map was written when the
UI carried ~18 endpoints (item under M-track docs). Eight flagship tabs shipped after it —
World (`GET /world`), Run (`POST /run`), North-Star (`POST /north-star`), Grand A/B/C/D
(`POST /compare/grand`), Analogues (`POST /analogues`), Time-series (`POST /timeseries`),
Data Fabric (`GET /data-fabric`) and Change-assumptions-and-rerun (`GET /assumptions` +
`POST /assumptions/rerun`) — so the table silently under-claimed and its "every documented
backend endpoint has a UI surface" line was no longer true. Documentation drift is a
§34 honesty issue: the map a judge reads must match the app they click.
- [x] Re-sync `frontend/README.md`: rewrite the intro surface list and the endpoint→SPEC table to cover all 28 analysis tabs in tab-bar order (North-Star/Run lead as the §37/§29 flagships), with exact endpoint paths verified against `lib/api.ts` (`/institutions/review`, `/parliament/failure-modes`, `/compare/grand`, `/assumptions/rerun`, …) and correct SPEC sections (§37, §5/§28.2, §7.1/§7.2, §21/§22, §4, §34.10); restore the accuracy of the "every documented backend endpoint has a UI surface" claim. Docs only, no code change; `tsc --noEmit` + `next build` already clean (SPEC §34)

## M31 — Surface the global sensitivity tornado (SPEC §24/§26)
The engine shipped `POST /sensitivity` after M30 declared the roadmap complete —
the one endpoint the UI hadn't surfaced. Where the Uncertainty tab (`POST
/uncertainty`) gives a Monte-Carlo fan for a *single* metric, this composes the
cheap, deterministic, cross-metric one-at-a-time (OAT) attribution a
decision-maker needs: sweep every documented assumption low→high edge (others at
default) and measure the swing in *every* headline metric's policy effect Δ(B−A),
then rank which assumptions the whole dashboard's answer rests on ("if you only
pin two numbers, pin these"). It introduces **no new numeric model** — every
value is a re-run of the same World-A/B/Δ path `/simulate` uses, and the swept
set is the same `ASSUMPTIONS` registry the §24 Uncertainty fan sweeps (single
source of truth), so the two can never disagree. Same rules: analysis Estimated,
underlying Δ metrics Simulated, no LLM on the numeric path, bar length is
leverage not likelihood, honest scope-limits, never fabricate a tornado when the
backend is down.
- [x] Sensitivity tab: `POST /sensitivity` → the cross-metric OAT tornado. Drive it from the compiled policy in the store with a Time-Machine horizon selector. Render a consistency banner (deterministic re-runs at documented assumption edges · no LLM · bar length = leverage-not-likelihood · interactions are the Uncertainty fan's job · same overridable set as the Uncertainty tab so they can't disagree), the plain-language `headline` of what the answer rests on, a **What-the-answer-rests-on** aggregate driver ranking (each assumption's mean influence-share across the dashboard as a leverage bar, with honest greyed-out "no effect here" rows for assumptions flat on every metric for this policy), and a **per-metric tornado** card per headline metric: its provenance tag, the default-assumption Δ(B−A), the most-influential assumption, and a signed bar per assumption spanning Δ-at-low → Δ-at-high with a default-Δ marker and the signed swing + %-of-default (up/down colouring, flat assumptions collapsed to a count). A collapsible §34 scope-limits list and the deterministic-attribution note close the tab. Analysis Estimated, underlying metrics Simulated (deterministic, no LLM); `idle` (no policy) / `loading` / `error` states when the backend is down, never mints a fabricated tornado (SPEC §24/§26/§34)

## M32 — Surface the Citizen View single-household drill-down (SPEC §17/§31)
The engine shipped `POST /citizen` (+ `GET /citizen/sample`) after M31 declared
the roadmap complete — the one endpoint the UI hadn't surfaced. Every other tab
aggregates the population; this exposes the SPEC §17 "click a household" view and
the SPEC §31 Agent-State data structure: one synthetic citizen's before/after
life through the Time Machine. It introduces **no new numeric model** — commute /
cost / mode reuse the same deterministic mode-choice model as `/simulate`, and
support reuses the same per-agent opinion model `/public` aggregates (the
far-horizon support equals this agent's contribution to the Public tab), so a
citizen's numbers can never disagree with the dashboard. Same rules: the
household is Simulated (synthetic micro-agent, SPEC §6 — never a real person), no
LLM on the numeric path, bands widen with the horizon, honest scope-limits,
never fabricate a life when the backend is down.
- [x] Citizen tab: `GET /citizen/sample` → a policy-independent "click a household" picker spanning the income spectrum, plus five archetype selectors (representative / most-burdened / biggest-loser / biggest-winner / median). `POST /citizen` → that household's staged Time-Machine trajectory: a consistency banner (same deterministic mode-choice model as `/simulate`, same per-agent opinion model as `/public`, no LLM), the household profile card (occupation / income band / age / household size / home+work zone / commute distance→CBD / car+transit access, all Simulated-tagged), a before→after topline (commute one-way, monthly transport cost, SPEC §31 policy support gauge with stance colouring), the Time-Machine table (World-A reference row + each checkpoint's mode, commute+cost with widening bands, monthly charge, support), the deterministic "Why?" narrative, a collapsible SPEC §31 Agent-State record table, and the collapsible `not_modelled` scope-limits. Everything Simulated (deterministic per-agent generalized-cost + cohort opinion model, SPEC §7.3/§13); no LLM on the numeric path; `idle` (no policy) / `loading` / `error` states + a graceful picker-unavailable fallback when the backend is down, never mints a fabricated household (SPEC §17/§31/§34)

## M33 — Surface the Business View single-firm drill-down (SPEC §17 Business View)
The engine shipped `POST /business` (+ `GET /business/sample`) after M32 declared
the roadmap complete — the one endpoint the UI hadn't surfaced. Where the Citizen
View follows one household, this follows one firm: the SPEC §17 "click a firm"
Business View. It introduces **no new numeric model** — labour accessibility
reuses the same deterministic mode-choice model as `/simulate` (the commute
generalized cost of the firm's own workers), and footfall / deliveries / cost /
revenue reuse the same economic coefficients as `/economy`, staged on the same
adaptation curve as the aggregate Time Machine — so a firm's numbers can never
disagree with the dashboard beside it. Same rules: the firm is Simulated
(synthetic micro-agent, SPEC §6 — never a real business), the revenue figure is
an Estimated proxy (before/after ratio only, never turnover), no LLM on the
numeric path, bands widen with the horizon, honest scope-limits, never fabricate
a firm when the backend is down.
- [x] Business tab: `GET /business/sample` → a policy-independent "click a firm" picker spanning sectors + the central/outer split, plus five archetype selectors (representative / most-exposed / biggest-footfall-loss / pedestrian-winner / largest). `POST /business` → that firm's staged Time-Machine trajectory: a consistency banner (same deterministic mode-choice model as `/simulate`, same `/economy` coefficients, same adaptation curve as the Time Machine, no LLM, revenue = Estimated proxy), the firm profile card (sector / building kind / zone / central-district / floors / floor area / estimated jobs, all Simulated-tagged), a before→after topline (daily footfall, labour-access index, deliveries, added annual cost with band, net revenue-proxy Δ%), the Time-Machine table (World-A reference row + each checkpoint's footfall+cost+revenue with widening bands, labour access, deliveries, added cost, net rev Δ%), the deterministic adaptation-decision cards, the deterministic "Why?" narrative, and the collapsible `not_modelled` scope-limits. Physical drivers Simulated (SPEC §7.3/§7.5), firm translation Estimated (SPEC §7.4/§8); no LLM on the numeric path; `idle` (no policy) / `loading` / `error` states + a graceful picker-unavailable fallback when the backend is down, never mints a fabricated firm (SPEC §17/§34)

## M34 — Re-sync the frontend README with the Citizen + Business drill-downs (SPEC §34)
The `frontend/README.md` surface map was last re-synced at the Sensitivity tab
(29 surfaces). Two single-agent drill-downs shipped after it — Citizen
(`POST /citizen` + `GET /citizen/sample`, M32) and Business (`POST /business` +
`GET /business/sample`, M33) — so the intro count and the endpoint→SPEC table
silently under-claimed and the "every documented backend endpoint has a UI
surface" line was no longer true. Documentation drift is a §34 honesty issue: the
map a judge reads must match the app they click.
- [x] Re-sync `frontend/README.md`: bump the intro "29 analysis surfaces" to 31 and add the Citizen/Business drill-downs to the intro list; add the two missing rows to the endpoint→SPEC table in tab-bar order (Citizen after World: `POST /citizen`, `GET /citizen/sample`, §17/§31; Business next: `POST /business`, `GET /business/sample`, §17), restoring the accuracy of the "every documented backend endpoint has a UI surface" claim. Docs only, no code change; `tsc --noEmit` + `next build` already clean (SPEC §34)

## M35 — Accessible, filterable analysis tab bar (SPEC §27 usability + a11y)
The lower-deck tab bar (SPEC §27) had grown to **31 panels** but was still a flat
row of plain buttons: it declared `role="tablist"`/`role="tab"` yet never
implemented the WAI-ARIA Tabs keyboard pattern, so a keyboard or screen-reader
user had to Tab through all 31 controls to reach a panel, tabs weren't linked to
their panels, and there was no way to find a panel by name. This is both a
usability wall for the demo and a real accessibility gap. Frontend-only, no new
endpoint, no numbers touched — a pure interaction/a11y upgrade to an existing
surface.
- [x] Upgrade `PanelTabs` to the ARIA APG Tabs pattern: a single tab stop with a **roving `tabIndex`** (only the selected tab is focusable), **ArrowLeft/ArrowRight/ArrowUp/ArrowDown/Home/End** navigation with automatic activation (wrapping, over only the currently-visible tabs), each tab wired to its panel via `id` + `aria-controls` + `aria-labelledby`, and the active `tabpanel` made focusable (`tabIndex=0`) so keyboard users can reach panel content; add a visible `:focus-visible` ring. Add a **filter box** (`type=search`, screen-reader-labelled, live `matched/total` count) that narrows the 31 tabs by label substring while always keeping the active tab visible (a narrow filter can never orphan the on-screen panel), with a "No panel matches …" status when empty; the guided demo clears the filter when it drives a tab so the requested panel stays in view. Refactored the 31 hand-written panel wrappers into a single `TABS` map (tab↔panel ids can't drift). Frontend-only; `tsc --noEmit` + `next build` + `next lint` clean (SPEC §27/§34)

## M36 — First frontend test suite: guard the honesty-critical pure helpers (SPEC §34)
The frontend had **zero automated tests** — `tsc`/`next build`/`next lint` catch
type and syntax errors but nothing pinned the *behaviour* of the pure helpers
that render every headline number and drive the editable-assumptions panel. A
silent regression in `formatNumber`/`formatSignedPct` corrupts the numbers a
judge reads (a §34 honesty surface), and a mutation bug in the DSL `setByPath`
helper would edit the wrong world or leak state between renders. These are the
highest-value, easiest-to-pin units in the codebase and had no guard at all.
Added with **zero new dependencies**: Node 22's built-in `node:test` +
`--experimental-strip-types` runs the TypeScript tests directly.
- [x] Add a `frontend/tests/` suite (`.test.mts`, run via `npm test` → `node --test --experimental-strip-types tests/*.test.mts`) covering `lib/format.ts` (every `formatNumber` magnitude bucket incl. sign-preservation on negatives; `formatSignedPct` sign rules — asserting the negative case uses a real U+2212 minus, not an ASCII hyphen — and the unsigned zero) and `lib/dsl.ts` (`getByPath` nested/missing/non-object-mid-path; `setByPath` leaf update **and its immutability guarantee** — original untouched, branch cloned, untouched branches independent — plus intermediate-object creation and non-object-intermediate replacement; `fieldKind` type→control mapping). 14 tests, all green; no dependency added, no runtime code changed; `tsc --noEmit` + `next build` + `next lint` still clean (SPEC §34)

## M37 — Surface the Minister's Brief export (SPEC §27/§37)
The engine shipped `POST /brief` (+ `GET /brief/example`) after M36 declared the
roadmap complete — the one endpoint the UI hadn't surfaced, the sibling of the
North-Star answer. Where North-Star renders the fixed §37 narrative as an
interactive panel, the Brief renders the *same* answer as a single, printable
Markdown memo — the one-page document a minister could read or print. It
introduces **no new numeric model**: the memo is a pure layout over
`/north-star`, which itself reuses every deterministic layer verbatim, so the
brief can never disagree with the tabs behind it (SPEC §34). Same rules:
provenance tags travel with the text, generated media stays labelled SIMULATED,
the Markdown is shown exactly as the backend produced it (no client-side
reformatting that could silently change a number or drop a tag), and nothing is
minted when the backend is down.
- [x] Brief tab: `POST /brief` → the North-Star answer as a self-contained Markdown memo. Input mirrors North-Star (compiled policy from the store, or a natural-language fallback that compiles first; horizon selector snapped to the Time-Machine checkpoints) plus an "include SIMULATED media section" toggle wired to the endpoint's `include_media`. On success: the provenance banner (Simulated numbers / Estimated transfers / Generated prose / no LLM in the numeric path) + the endpoint's own honesty `note`, a memo-meta card (title, echoed minister's question, horizon label, `policy_id`, `rendered from /north-star`, word count), the backend-supplied provenance key rendered as tagged legend rows, an export toolbar (Copy Markdown via the Clipboard API with a graceful disabled state when unavailable, Download `.md` via a Blob object-URL named `ministers-brief-<policy_id>.md`), and the memo itself in a scrollable monospace block shown **verbatim** so no figure or provenance tag can be altered client-side. Added `BriefRequest`/`BriefResponse`/`TagLegendEntry` types + `runBrief()` to `lib/api.ts`; registered the tab right after North-Star (its sibling composed-answer surface). `idle` (no policy) / `loading` / `error` states + a retry that never mints a fabricated memo when the backend is down; re-synced `frontend/README.md` (31→32 surfaces, new endpoint→SPEC row). `tsc --noEmit` + `next build` + `next lint` clean (SPEC §27/§37/§34)

## M38 — Surface the decision-under-uncertainty layer (Robustness tab, SPEC §20/§21/§22)
The engine shipped `POST /robustness` (+ `GET /robustness/objectives`) after M37
declared the roadmap complete — a decision layer one level above the Stress tab.
Where Stress asks *"does **this** policy hold under the named shocks?"*, Robustness
asks the question a minister actually faces: *"given several candidate policies and
a set of possible futures, **which candidate should I pick** — the headline winner,
or the one least bad when the world turns out otherwise?"*. It introduces **no new
numeric model**: every payoff is the same deterministic Simulated Δ(B−A) the
Stress/Simulate endpoints return, composed across candidates × states, so a
candidate's numbers can never disagree with the tabs beside it (SPEC §22/§34). The
candidate set is the compiled policy plus **transparent design variants of it**,
derived client-side through the same structured amendment loop the app already uses
(`applyAmendment`) and re-simulated by the backend — the UI invents no numbers.
- [x] Robustness tab: `GET /robustness/objectives` → the objective menu; `POST /robustness` → rank candidates under uncertainty. Candidate slate = the compiled policy (candidate one, un-amended) + user-toggleable design variants (half/higher charge, transit-funded, general-fund, low-income exempt), each a compiled DSL via `applyAmendment` so the backend re-simulates it through the same deterministic A/B/Δ core (no invented numbers). On success: a provenance tag (Simulated, no LLM), a headline banner that calls out whether robustness **flips** the choice away from the nominal winner (with objective/direction/horizon/state count), a five-criterion decision-picks grid (nominal / maximin / minimax-regret-Savage / Laplace / most-robust, each highlighting agreement-or-divergence vs the headline winner), a candidate scorecard (nominal / worst-case / mean payoff, max regret, robustness rate with holds/fails counts), a full **regret matrix** (candidates × states, per-state best=0 highlighted and each row's max-regret flagged, with per-state confidence that widens with the horizon), and a collapsible method/provenance note. Objective + horizon selectors; `idle` (no policy) / `loading` / `error` states + a graceful objective-menu fallback (run with the backend default) and never mints a decision when the backend is down (SPEC §20/§21/§22/§34). Added `RobustnessReport`/`RobustnessCandidateScore`/`RobustnessStateResult`/`RobustnessDecisionPicks`/`RobustnessObjectives` types + `runRobustness()`/`fetchRobustnessObjectives()` to `lib/api.ts`; registered the tab right after Stress (its decision-layer sibling); re-synced `frontend/README.md` (32→33 surfaces, new endpoint→SPEC row + prose). `tsc --noEmit` + `next build` + `next lint` + `npm test` (14) all clean

## M39 — Guard the client-side city model: the numbers the timeline paints (SPEC §34)
M36 stood up the first frontend test suite but deliberately scoped it to the two
smallest honesty helpers (`lib/format.ts`, `lib/dsl.ts`). The largest untested
§34 surface was still `lib/cityModel.ts` — the deterministic, closed-form cordon
demand-response model that the 10-year timeline scrubber runs **client-side**, so
the visual city can update per-frame without a network round-trip. Every number
that model emits (car mode share, transit shift, vehicle-km, CO₂, congestion,
support) is painted straight onto the 3D city and the simple-view dashboard, and
`deltaPct` renders the "% vs do-nothing" figures beside them. Nothing but these
pure functions guards those numbers: a silent regression corrupts exactly what a
judge reads while dragging the timeline, with no backend in the path to catch it.
The module is deterministic, so its arithmetic can be pinned exactly and its
model behaviour pinned against the documented invariants and bounds.
- [x] Add `frontend/tests/cityModel.test.mts` (picked up automatically by the existing `tests/*.test.mts` glob, still zero new dependencies) covering `lib/cityModel.ts` and the OD helper `lib/city.ts`: `cityConstants` (trip sums, CBD-vs-citywide split, trip-weighted mean distances, and the empty-matrix guard that must return zeros not NaN); `inflowByZone` (per-destination aggregation + empty map); `deltaPct` (signed change, exact-zero, and the zero/NaN/Infinity reference guard that returns `null` so no Infinity/NaN leaks into a headline); and `predict` invariants — year-0 mode shares equal today's split because the behavioural ramp is zero, the 0–10 horizon is clamped at both ends, the charge suppresses CBD car share / cuts CO₂ / shifts trips onto transit vs do-nothing, public realm ramps in slowly (~none day one, most by y6), baseline demand drifts up with background growth, **every output stays within its documented bounds** (support 0.05–0.95, congestion 0–1.6, shares in 0–1, trips never negative, all finite) swept across all scenarios × the 0–10 horizon, and the provenance chain that CO₂ is *exactly* vehicle-km × the single published tailpipe factor (no hidden fudge). 14 new tests (28 total), all green; no runtime code changed; `tsc --noEmit` + `next build` + `next lint` still clean (SPEC §34)

## M40 — Guard the amendment transform behind the killer interaction (SPEC §29/§34)
`applyAmendment` (in `lib/api.ts`) is the pure DSL transform behind two of the
app's load-bearing interactions: the "apply amendment + re-simulate" loop (SPEC
§29, the killer demo moment) and the Robustness tab's candidate slate (M38), where
each design variant is an `applyAmendment(policy, …)` the backend then simulates
through the deterministic A/B/Δ core. It was untested. A bug here is a §34
correctness failure with no backend to catch it: a leaked mutation of the base
policy, a duplicated exemption, a mis-rounded charge, or a revenue split that no
longer sums to 1 all mean the app hands the engine a policy that isn't the one the
label claims — and every downstream number is silently for the wrong world.
- [x] Add `frontend/tests/amendment.test.mts` (auto-picked by the `tests/*.test.mts` glob, zero new deps) pinning `applyAmendment`: immutability of the input policy (re-simulate must be side-effect-free), the labelled-id slug (`<id>__<label with spaces→_>`), `set_charge_amount` outright replace, `charge_multiplier` scaling the existing charge with the 4-dp rounding that keeps a clean figure on screen, the compose order (set-amount **then** multiplier hits the new amount), exemptions appending without a case-insensitive duplicate (both the fresh add and the re-apply-to-an-already-exempt-policy path), the revenue split being rewritten to sum to exactly 1, and tolerance of a bare policy with no intervention/exemptions block. 8 new tests (36 total), all green; no runtime code changed; `tsc --noEmit` + `next lint` clean (SPEC §29/§34)

## M41 — Example-policy gallery: one click per distinct mechanism (SPEC §3/§7.5/§34)
M40 declared the roadmap complete again, but the engine track had meanwhile made
three of the app's pricing families **numerically distinct** — the cordon
congestion charge, the low-emission zone (charges only non-compliant vehicles;
dominant lever is fleet turnover, not mode shift) and the workplace parking levy
(levied on employers per space, only partly passed through to the commuter) — so
the twin now gives an honestly *different* answer for each, plus pedestrianisation
(a non-pricing access restriction) and a charge-and-reinvest transit variant. The
compiler UI, though, shipped a single hardcoded congestion-charge "Load demo
policy" button, so a judge had no way to discover — let alone one-click compare —
the mechanisms the engine works hard to tell apart. This item is pure
discoverability: worked plain-language prompts, one per mechanism. It mints **no
numbers** — clicking a chip only fills the draft box; the backend still compiles
and simulates, and each chip's note frames the *mechanism and the comparison to
make*, never a predicted figure (SPEC §34).
- [x] Replace the lone "Load demo policy" button with an example-policy gallery in `PolicyCompiler`: five curated prompts (`EXAMPLE_POLICIES`), one per mechanism family — cordon congestion charge (the §29 demo, still the default), low-emission zone, workplace parking levy, pedestrianisation, and a 100%-transit-reinvested charge — each rendered as a toggle chip carrying a mechanism tag + a `title`/inline "what to watch" note that describes the lever and the comparison, not an outcome. Clicking one loads its text and **resets any compiled result to `idle`** so a prior policy's numbers can never linger under a different policy's text; a manual textarea edit clears the active-example highlight so no chip claims to match hand-edited text. Prompts are grounded in the engine's documented §7.5 mechanisms (verified in `ROADMAP_ENGINE.md`), so each compiles to a real, distinct DSL — the UI invents nothing. Added `.example-gallery`/`.example-chips`/`.example-btn` styles to `globals.css`. `tsc --noEmit` + `next build` + `next lint` + `npm test` (36) all clean (SPEC §3/§7.5/§34)

## M42 — Surface the two new honest mechanisms: time-of-day pricing + standalone transit (SPEC §7.5/§9/§34)
After M41's gallery shipped, the engine track landed two more *numerically distinct*
mechanisms (commit f5852af) that no frontend surface exposed. (1) A charge's
`active_hours` now actually scale the per-trip signal: the engine prices only the
overlap of the operating window with the inbound AM commute peak, so an all-day
cordon and a late-starting one no longer produce byte-identical numbers (previously
they did — dishonest per §34). (2) A **standalone** `transit_investment` policy
(no charge, no ban) is recovered as a real supply-side lever (fare cut + speed
uplift, ramped in long-run), where before it was a silent no-op. The gallery had a
chip for neither: no way to see that *when* a charge operates changes the answer, and
no way to try a pure-carrot policy distinct from the "charge + reinvest" chip. Pure
discoverability — the chips mint no numbers; the backend still compiles and
simulates each, and both prompts were verified against the rule-based compiler to
produce the intended DSL (road_pricing @ 08:30–18:00 → coverage 0.5; transit_investment,
general-fund, no charge).
- [x] Add two chips to `PolicyCompiler`'s `EXAMPLE_POLICIES`: a "Late-start charge" (mechanism *Time-of-day pricing*) — the same 12-credit cordon but operating 8:30am–6pm so it covers only half the inbound peak, whose `watch` frames the timing→attenuation comparison against the all-day cordon, not a figure; and a "Fund buses, no charge" (mechanism *Transit supply*) — a pure carrot (cheaper/faster/more-frequent buses, general-fund, no charge/ban) whose `watch` frames the honest missing-stick guardrail (car drop ≤ transit gain) versus every pricing scheme. Both prompts grounded in the engine's §7.5 mechanisms and verified against the rule-based compiler so each yields the intended distinct DSL (the UI invents nothing; SPEC §34). No new types, styles, or endpoints — the existing chip loader, active-example highlight, and idle-reset all apply unchanged. `tsc --noEmit` + `next build` + `next lint` + `npm test` (36) all clean (SPEC §7.5/§9/§34)

## M43 — Surface the active-travel reinvestment mechanism (SPEC §7.5/§9/§34)
After M42's two chips shipped, the engine track landed one more *numerically
distinct* mechanism (commit 61dd8ec): `revenue_allocation.active_travel` — a
first-class, LLM-extractable DSL field — used to be a silent no-op (the
revenue→service lever read only `public_transport`), so a policy spending 100% of
charge revenue on cycle lanes/pavements produced byte-identical traffic/emissions
to banking it in the general fund. It now drives an
`active_travel_speed_multiplier = 1 + share·0.20` (Estimated) that scales
active-travel speed and the max walkable/cyclable distance in World B, pulling the
nearest-margin short-trip car/transit commuters onto foot/bike — engaging only when
the charge actually raises revenue and ramping over the horizon like transit
reinvestment (§9). The gallery had no chip for it: no way to see that *where* a
charge's revenue goes (buses vs. bike lanes) changes which trips move and how.
Pure discoverability — the chip mints no numbers; the backend still compiles and
simulates it, and the prompt was verified against the rule-based compiler
(`.venv/bin/python … parse_policy`) to yield the intended distinct DSL
(road_pricing 12-credit cordon, `revenue_allocation.active_travel = 0.8`,
`public_transport = 0.0`) — the active-travel-dominant split the new lever bites on.
- [x] Add a "Charge, fund cycling" chip (mechanism *Active-travel reinvest*) to `PolicyCompiler`'s `EXAMPLE_POLICIES`: the same 12-credit cordon but spending 80% of revenue on protected cycle lanes and wider pavements, whose `watch` frames the where-does-revenue-go comparison against the bus-funded charge (different destination for displaced trips) and the honest neutral-until-revenue guardrail (§9), never a figure. Placed between the "Bus-funded charge" and "Fund buses, no charge" chips so the three revenue-destination levers sit together. Prompt grounded in the engine's §7.5 mechanism and verified against the rule-based compiler so it yields the intended active-travel-dominant DSL (transit is matched first, so no transit percentage is mentioned — the UI invents nothing; SPEC §34). No new types, styles, or endpoints — the existing chip loader, active-example highlight, and idle-reset all apply unchanged. `tsc --noEmit` + `next build` + `next lint` + `npm test` (36) all clean (SPEC §7.5/§9/§34)

## M44 — Surface the stated-equity-constraint compliance check (SPEC §7.3/§34)
After M43, the engine track landed a §34 honesty feature the frontend never
surfaced (commits baf09f3/be16d16): the microsim now *tests* a policy's own
stated `constraints.max_low_income_burden_increase_pct` cap against the modelled
low-income-decile charge burden, returning a `constraint_check`
(cap_pct / modelled_low_income_burden_pct / satisfied / margin_pct / note) on the
`MicrosimReport`. Until now that cap was recorded and asserted in debate but never
checked against the numbers — SPEC §34's "a constraint you never test is theatre."
The `MicrosimPanel` neither typed nor rendered the field, so a judge compiling a
policy that declares an equity cap had no way to see whether the twin's own model
says the policy *keeps that promise* — or breaks it. Pure surfacing of real
backend data: the card mints no numbers, shows the engine's own note verbatim, is
tagged with the report's provenance, and disappears entirely when a policy states
no cap.
- [x] Type `ConstraintCheck` + `MicrosimReport.constraint_check` in `lib/api.ts` and add a pure, unit-tested `constraintVerdict` mapper that (honestly, §34) marks a zero-modelled-burden pass as *moot* rather than an actively-met promise, an in-cap real burden as *pass*, and any overshoot as a hard *fail* (never softened; trusts the engine's `satisfied` flag which carries the cap+epsilon logic). Render a `ConstraintCheckCard` in `MicrosimPanel` between the winners headline and the regressivity card — ✓/✕ glyph, pass/violated/moot verdict pill, cap-vs-modelled + signed headroom/overshoot meta, the engine's plain-language note, and the report's provenance tag — shown only when `constraint_check` is present. Added `.ms-constraint*` styles to `globals.css` mirroring the regressivity card. New `tests/microsim.test.mts` (5 tests, 41 total). `tsc --noEmit` + `next build` + `next lint` + `npm test` (41) all clean (SPEC §7.3/§34)

## M45 — Fix the gallery chips so the keyless rule-based fallback actually applies the charge (SPEC §7.5/§29/§34)
Verifying M44's constraint card reachability surfaced a latent, high-impact demo
bug in the gallery-chip prompts (`EXAMPLE_POLICIES`, frontend-owned). With **no
LLM key configured** — the default in this environment — the policy compiler goes
straight to the rule-based parser, whose `_find_amount` recognises `£12`, `12
pounds`, or `charge/fee/levy of 12`, but **not** `12 credits` (Meridia's fictional
currency). Six of the eight chips phrased the charge as "…12 credits to enter…",
so they compiled to `intervention.amount = None` → a zero-charge policy →
all-zero microsim (0 payers, 0 regressivity) and a hollow constraint card. Worse,
the low-emission-zone chip's "…that charges 12 credits … entering…" tripped the
`charge.*enter` road-pricing classifier *before* the LEZ rule, so it compiled as a
plain cordon — the exact mechanism M41 claimed it was distinct from. M41–43 had
verified mechanism/coverage/revenue-split but never the charge amount, so this
slipped through. Pure prompt wording (frontend-only): no numbers invented, every
DSL field re-verified against the rule-based compiler + microsim.
- [x] Reword the six charge-bearing `EXAMPLE_POLICIES.text` prompts so the rule-based `_find_amount` extracts the 12-credit charge: the four cordon variants (default, late-start, bus-funded, cycle-funded) and the LEZ now say "Introduce a charge of 12 credits on private vehicles entering…" / "…with a daily levy of 12 credits on … non-compliant vehicles, in force between…" (the LEZ avoids the `charge.*enter` trigger so it classifies as `low_emission_zone`, not road pricing). Workplace-parking-levy ("levy of 12"), pedestrianisation and standalone-transit already parsed correctly and are unchanged. Verified end-to-end against the backend rule-based compiler + `build_microsim_report`: all six now yield `amount = 12` with their intended distinct mechanism (road_pricing ×4 / low_emission_zone / parking_levy), nonzero payers (92–1032) and live regressivity, while the two no-charge chips keep `amount = None` — so under the keyless fallback the gallery, microsim, regressivity and M44 constraint card all show real, distinct numbers instead of zeros (SPEC §34). No new types/styles/endpoints; hours, exemptions, revenue splits and the 5% low-income cap all preserved. `tsc --noEmit` + `next build` + `next lint` + `npm test` (41) all clean (SPEC §7.5/§29/§34)
