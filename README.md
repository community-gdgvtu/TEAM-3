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

## Stack

- **Frontend:** Next.js + TypeScript, MapLibre + deck.gl (3D map), timeline scrubber
- **Backend:** Python + FastAPI, DuckDB, numerical + agent-based simulation services
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
