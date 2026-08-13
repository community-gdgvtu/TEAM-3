# URBAN frontend

Next.js (App Router) + TypeScript UI for the URBAN policy digital twin — a 3D city,
a time-machine timeline, a tagged outcomes dashboard, and a tab bar of 33 analysis
surfaces: the flagship North-Star answer (§37) and the Minister's Brief export that
renders it as a printable memo (§27/§37), the one-call Run pipeline (§29), the
browsable baseline World Model (§5), the Citizen and Business single-agent
drill-downs (§17/§31), Parliament, Public reaction, Press, Press
conference, Red Team, Counterfactual + Grand A/B/C/D compare, SDG, Diffusion, Ensemble,
Uncertainty, Sensitivity, Optimiser, Economy, Dynamics, Microsim, Spatial,
Stress-testing, Decision-under-uncertainty (Robustness), Analogues, Time-series,
Institutions, Backtest, Registry, Reproduce, Data Fabric, and
Change-assumptions-and-rerun.

## Run

```bash
cd frontend
cp .env.local.example .env.local   # points at the backend, default http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

The backend must be running for the landing page's health check to go green:

```bash
cd backend
uvicorn app.main:app --reload      # http://localhost:8000
```

Every panel independently handles idle / loading / error / "waiting for backend"
states, so the UI is usable and honest even before a given endpoint is live.

## Scripts

- `npm run dev` — dev server
- `npm run build` — production build
- `npm run start` — serve the production build
- `npm run lint` — ESLint (next/core-web-vitals)
- `npm run typecheck` — `tsc --noEmit`

## Config

- `NEXT_PUBLIC_API_BASE_URL` — base URL of the FastAPI backend (browser-reachable).

## Architecture

```
app/
  page.tsx            landing: health check + policy compiler entry
  layout.tsx          root layout, theme tokens (globals.css)
  HealthStatus.tsx    GET /health poller
  PolicyCompiler.tsx  natural-language draft → POST /policy/compile (Generated DSL)
  error.tsx           App Router segment error boundary (crash-safe recovery card)
  global-error.tsx    root error boundary (self-contained html/body)
  not-found.tsx       themed 404
components/
  map/                MapLibre GL + deck.gl city (zones, roads, cordon, overlays)
  twin/               the workspace: store, timeline, dashboard, and one panel per endpoint
lib/
  api.ts              typed fetch client for every backend endpoint; MetricTag types
  city.ts, dsl.ts, format.ts, demo.ts   geometry, DSL helpers, number formatting, tour script
```

State flows through `components/twin/TwinStore.tsx`: a compiled policy + `/simulate`
result feed the map overlays, the `TimelineScrubber` (T0→10y checkpoints), and the
`Dashboard` tiles. The `PanelTabs` bar switches the analysis surfaces below; the
`DemoTour` launcher drives that bar for the 60-second walkthrough (SPEC §29).

## Analysis surfaces → endpoint → SPEC

Every documented backend endpoint has a UI surface. All fetches are typed in `lib/api.ts`.
The core landing/canvas surfaces come first; the rest follow the analysis tab-bar order a
judge sees left-to-right (North-Star and Run lead as the §37/§29 flagships).

| Surface | Endpoint | SPEC |
| --- | --- | --- |
| Landing health check | `GET /health` | — |
| Policy compiler | `POST /policy/compile` | Step 2 |
| 3D city map + baseline | `GET /baseline` | §17/§27 |
| Simulate / re-simulate | `POST /simulate` | §29 |
| Outcomes dashboard tiles | (from `/simulate` + `/baseline`) | §27 |
| Evidence drawer | `POST /evidence`, `GET /evidence/example` | §26 |
| North-Star answer (the minister's question) | `POST /north-star`, `GET /north-star/example` | §37 |
| Minister's Brief (North-Star as a printable Markdown memo) | `POST /brief`, `GET /brief/example` | §27/§37 |
| Run — whole pipeline in one call | `POST /run`, `GET /run/example` | §28/§29 |
| Baseline World Model | `GET /world` | §5/§28.2 |
| Citizen View (click a household) | `POST /citizen`, `GET /citizen/sample` | §17/§31 |
| Business View (click a firm) | `POST /business`, `GET /business/sample` | §17 |
| Parliament debate + amendment | `POST /parliament/debate`, `POST /simulate/amend` | §11/§12 |
| Public reaction | `POST /public` | §13 |
| Simulated press feed | `POST /media` | §15 |
| Press conference (presser) | `POST /press-conference` | §16 |
| Red Team (Failure Mode Register) | `POST /parliament/failure-modes` | §11 |
| Counterfactual compare | `POST /compare` | §21 |
| Grand A/B/C/D compare | `POST /compare/grand` | §21/§22 |
| SDG alignment | `POST /sdg` | §23 |
| Opinion diffusion | `POST /diffusion` | §14 |
| Ensemble forecast | `POST /ensemble` | §8 |
| Uncertainty fan | `POST /uncertainty` | §24 |
| Sensitivity tornado | `POST /sensitivity` | §24/§26 |
| Policy optimiser | `POST /optimise` | §22 |
| Economic spillover | `POST /economy` | §7.4 |
| Recursive feedback loop (dynamics) | `POST /dynamics` | §7.6/§19 |
| Distributional microsimulation | `POST /microsim` | §7.3 |
| Spatial traffic assignment | `POST /spatial` | §7.7 |
| Stress-testing environment | `GET /stress-test/catalogue`, `POST /stress-test` | §20 |
| Decision under uncertainty (Robustness) | `GET /robustness/objectives`, `POST /robustness` | §20/§21/§22 |
| Historical analogues (difference-in-differences) | `POST /analogues` | §7.1/§8 |
| Time-series forecast | `POST /timeseries` | §7.2/§8 |
| Institutional review | `POST /institutions/review` | §18 |
| Backtest scorecard | `GET /backtest/example`, `POST /backtest` | §25 |
| Model registry / transparency | `GET /registry` | §33 |
| Reproducibility manifest (REPRODUCE RUN) | `POST /reproduce` | §32 |
| Data Fabric catalogue | `GET /data-fabric` | §4 |
| Change-assumptions-and-rerun | `GET /assumptions`, `POST /assumptions/rerun` | §34.10 |

## Honesty contract in the UI (SPEC §34)

The product guardrail is non-negotiable: the LLM never generates core numeric effects,
every number is provenance-tagged, generated media is stamped SIMULATED, and long-run
uncertainty widens. Here is how the frontend enforces that — none of it is decorative:

- **Provenance chips.** `lib/api.ts` types every value's `MetricTag` as one of
  `Observed | Estimated | Simulated | Generated`. Tiles and panels render it as a
  coloured chip — `<span className={`tag ${tag.toLowerCase()}`}>` → `.tag.observed`,
  `.tag.estimated`, `.tag.simulated`, `.tag.generated` in `globals.css`. Simulation
  effects show **Simulated**; the compiled DSL shows **Generated**; synthetic benchmark
  actuals in the backtest show a distinct **synthetic** chip.
- **Never a fabricated policy effect.** Before a `/simulate` result exists, a metric tile
  shows the real baseline (World-A) value and a "vs baseline" placeholder ("simulate a
  policy") — it never prints an invented Δ. Metrics with no series (Equity, Support)
  render an explicit "Awaiting model" placeholder rather than a number.
- **Visible uncertainty.** Tiles pair each value with a sparkline band and a ± range;
  the Uncertainty fan surfaces Monte-Carlo 50/80/95% bands that widen with horizon; the
  Ensemble panel shows a disagreement band across three independent methods (band =
  method disagreement, not false precision).
- **SIMULATED media.** `/media` and `/press-conference` output carries a mandatory
  SIMULATED banner; outlets are fictional and the prose is **Generated** over
  **Simulated** figures — never presented as real coverage.
- **Waiting for backend.** When an endpoint isn't live, its panel shows a clear
  "waiting for backend" state instead of cached or invented values.
- **Crash-safe.** `app/error.tsx` / `app/global-error.tsx` contain any render throw
  (bad payload shape, deck.gl/MapLibre runtime error, deep null deref) to a themed
  recovery card with the error digest — it never fabricates or estimates a metric to
  paper over a failure.

The **Registry** tab (`GET /registry`) is the machine-readable counterpart: model cards
(method, determinism, LLM-role, output tag), data sources, the live assumption index, and
the SPEC §34 guardrail checklist with pass/fail.

The **Reproduce** tab (`POST /reproduce`, SPEC §32) turns a run into an auditable record:
a content-addressed `run_id` (SHA-256 of the exact policy DSL, seed, dataset byte-hashes,
code version and live assumptions — timestamp excluded, so identical inputs always yield
the same key), dataset + model versions, and a self-verified `output_digest`. The
`reproducible` flag is *proven* — the backend runs the deterministic core twice and
compares digests — and `prompts` is always empty, surfacing the §34 guarantee that no LLM
enters the numeric path. When the backend is down the panel says so rather than minting a
fake key.

The **Stress-testing** tab (`GET /stress-test/catalogue` + `POST /stress-test`, SPEC §20)
answers "does the policy still work under a recession + fuel shock?" without over-claiming.
Each named shock is a transparent scenario assumption applied to *both* worlds, so the
reported Δ(B−A) still isolates the policy; policy deltas are **Simulated** (deterministic,
no LLM) while the shock magnitudes are **Estimated** — both provenance classes are shown.
Crucially, every shock declares a model `fidelity` (modelled / partial / proxy) and a
plain-language caveat (a flood, heatwave or interest-rate move is only a proxy in a static
mode-choice core), so a weakly-represented shock never masquerades as a precise result. The
per-metric "retained" bar carries a 100%-of-baseline marker so a weakened or reversed
benefit is visible at a glance, and when the backend is down the panel shows a
waiting/error state rather than a fabricated robustness verdict.

The **Decision-under-uncertainty (Robustness)** tab (`GET /robustness/objectives` +
`POST /robustness`, SPEC §20/§21/§22) sits one level above the Stress tab: instead of
asking whether *one* policy holds, it compares *several candidate policies* across the
baseline and every §20 shock and reports which candidate each classic decision rule picks —
the headline (nominal) winner, the worst-case (maximin) choice, the least-regret (Savage)
choice, the equal-weight (Laplace) choice and the stress-test robustness rate. The candidate
set is the compiled policy plus **transparent design variants of it** (halve/raise the
charge, redirect revenue, exempt low-income), each derived client-side through the same
structured amendment loop the app already uses and re-simulated by the backend — no number
is invented in the UI, every payoff is the same **Simulated** Δ(B−A) the Stress tab returns.
The headline banner calls out the demo's point — whether admitting uncertainty *flips* the
choice away from the headline winner — and a regret matrix shows, per state, how much worse
each candidate is than the best choice for that state. When the backend is down the panel
shows a waiting/error state rather than minting a decision.
