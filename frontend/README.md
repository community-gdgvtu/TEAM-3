# URBAN frontend

Next.js (App Router) + TypeScript UI for the URBAN policy digital twin — a 3D city,
a time-machine timeline, a tagged outcomes dashboard, and a tab bar of analysis surfaces
(Parliament, Public reaction, Press, Counterfactuals, Uncertainty, Optimiser, SDG,
Diffusion, Ensemble, Institutions, Backtest, Registry).

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

| Surface | Endpoint | SPEC |
| --- | --- | --- |
| Landing health check | `GET /health` | — |
| Policy compiler | `POST /policy/compile` | Step 2 |
| 3D city map + baseline | `GET /baseline` | §17/§27 |
| Simulate / re-simulate | `POST /simulate` | §29 |
| Outcomes dashboard tiles | (from `/simulate` + `/baseline`) | §27 |
| Evidence drawer | `POST /evidence` | §26 |
| Parliament debate + amendment | `POST /parliament/debate` | §11 |
| Red Team (Failure Mode Register) | (from `/parliament/debate`) | §11 |
| Public reaction | `POST /public` | §13 |
| Simulated press feed | `POST /media` | §15 |
| Press conference (presser) | `POST /press-conference` | §16 |
| Counterfactual compare | `POST /compare` | §21 |
| SDG alignment | `POST /sdg` | §23 |
| Opinion diffusion | `POST /diffusion` | §14 |
| Ensemble forecast | `POST /ensemble` | §8 |
| Uncertainty fan | `POST /uncertainty` | §24 |
| Policy optimiser | `POST /optimise` | §22 |
| Institutional review | `POST /institutions` | §18 |
| Backtest scorecard | `GET /backtest/example`, `POST /backtest` | §25 |
| Model registry / transparency | `GET /registry` | §33 |

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
