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

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## Development

This project is being built by an autonomous development loop. Progress is tracked in
[`ROADMAP.md`](./ROADMAP.md). Each iteration picks the next unchecked item, implements it,
and commits. See [`AGENT_LOOP.md`](./AGENT_LOOP.md) for the loop contract.

## Epistemic rule

URBAN never presents a synthetic future as fact. Every output is tagged
`Observed | Estimated | Simulated | Generated`, and LLMs never produce core numeric effects.
