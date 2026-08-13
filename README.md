# URBAN — Policy Digital Twin

> **Run the policy before you run the country.**

URBAN is a policy simulation environment: a hybrid mechanistic + LLM system that lets
policymakers test, stress-test, debate, and optimise policies before deploying them in
the real world. See [`SPEC.md`](./SPEC.md) for the full product spec.

This repo targets the **hackathon vertical slice** (SPEC §28): a CBD congestion-pricing /
pedestrianisation demo that proves the closed loop:

```
policy → baseline twin → simulation → time machine → parliament → amendment → re-sim → media
```

## The screen

The default view is deliberately small: **pick one of three policies, drag ten
years, watch the city change.**

Meridia is a *prebuilt* 3D city bundled in this repo — ~1,000 building footprints
with real heights, a street grid, a river, parks and a charge cordon. Dragging
the scrubber morphs it:

| you drag | the city does |
| --- | --- |
| any year | pipeline buildings break ground (amber) and top out |
| transit is funded | towers near the core grow — transit-oriented development |
| pedestrianisation lands | low-rise central kerbside converts to plazas and pocket parks |
| traffic responds | street trails thin out and speed up; the cordon recolours |
| mode split shifts | the commute arcs go from car-amber to transit-blue |

That projection runs **in the browser** (`frontend/lib/cityModel.ts`) so scrubbing
is instant and the demo works with the backend down. It is a closed-form summary
of the same mechanism the FastAPI engine runs step-wise, off the same OD matrix
and the same input assumptions (`backend/app/baseline/params.py`).

Everything else — the plain-language policy compiler, the agent-based engine with
uncertainty bands, the evidence drawer, parliament / public / press / red team /
optimiser — is unchanged and sits behind the **Advanced** disclosure at the
bottom of the page. It needs the backend running.

### Data lineage

Meridia is synthetic — not a real place, no real administrative record. It is
shaped like two real, open data models, cited in-app under "Data sources & how
the prediction model works" and in `data/city/sources.json`:

- **3D geometry** — [3DCityDB Web Map Client](https://github.com/3dcitydb/3dcitydb-web-map)
  (Apache-2.0; CityGML / Cesium 3D Tiles / glTF). The building layer follows the
  same LOD1 shape a 3DCityDB export uses: one footprint polygon per building with
  a height attribute, grouped by zone. Swapping in a real city means replacing
  `buildings.geojson` with a 3DCityDB export — the scene reads footprint + height
  and nothing else.
- **Travel demand** — [ONS 2011 Census origin–destination table WU03EW](https://www.nomisweb.co.uk/census/2011/wu03ew)
  (UK, Open Government Licence v3.0): home-zone → work-zone daily commuter flows
  by mode. `data/city/od_pairs.json` is a destination-constrained gravity model
  written to the same schema, so a real WU03EW extract drops into the same pipeline.

## Stack

- **Frontend:** Next.js + TypeScript, deck.gl (3D city, no basemap or tile server), timeline scrubber
- **Backend:** Python + FastAPI, MongoDB, numerical + agent-based simulation services
- **AI layer:** LLM agents for policy parsing, parliament debate, devil's advocate, media (never numeric effects)

## Quick start

**Prerequisites:** Python 3.11+ and Node 18+.

### One command (recommended)

```bash
./scripts/dev.sh
```

This sets up the backend virtualenv, installs backend + frontend dependencies on
first run, generates the synthetic city dataset if missing, then starts **both**
servers:

- Backend (FastAPI) → <http://localhost:8000> (interactive docs at `/docs`)
- Frontend (Next.js) → <http://localhost:3000>

Press `Ctrl-C` to stop both. Useful variants:

```bash
./scripts/dev.sh setup      # install deps + generate data, then exit
./scripts/dev.sh backend    # backend only
./scripts/dev.sh frontend   # frontend only

# override ports (defaults 8000 / 3000)
BACKEND_PORT=8010 FRONTEND_PORT=3010 ./scripts/dev.sh
```

The frontend is pointed at the backend automatically via `NEXT_PUBLIC_API_BASE_URL`.

### Manual (two terminals)

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

### Verify it's running

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"URBAN Policy Digital Twin",...}
```

Then open <http://localhost:3000> — the landing page fetches `/health` and shows
the backend status live.

## Development

This project is being built by an autonomous development loop. Progress is tracked in
[`ROADMAP.md`](./ROADMAP.md). Each iteration picks the next unchecked item, implements it,
and commits. See [`AGENT_LOOP.md`](./AGENT_LOOP.md) for the loop contract.

## Epistemic rule

URBAN never presents a synthetic future as fact. Every output is tagged
`Observed | Estimated | Simulated | Generated`, and LLMs never produce core numeric effects.
