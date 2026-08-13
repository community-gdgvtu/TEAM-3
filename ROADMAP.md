# ROADMAP — Hackathon Vertical Slice

Ordered, incremental milestones. The autonomous dev loop works **top to bottom**: pick the
first unchecked `[ ]` item, implement it end-to-end, check it off, commit, push.
Keep each commit small and working. Prefer a running demo over completeness.

Demo policy: *Pedestrianise / price vehicles entering a central district and reinvest revenue into public transport.*

## M0 — Scaffold & infra
- [x] Repo, spec, roadmap, agent-loop contract
- [x] Backend: FastAPI app skeleton + `/health` + CORS, `requirements.txt`
- [x] Frontend: Next.js + TS app skeleton, landing page, calls `/health`
- [x] Shared demo dataset: synthetic city grid (zones, roads, OD pairs) in `data/`
- [x] Dev runner script + basic README run instructions verified

## M1 — Policy compiler (NL → Policy DSL)
- [x] `POST /policy/compile`: NL policy text → structured Policy DSL (SPEC §3) via LLM, with fallback rule-based parser
- [x] Frontend policy input box + editable extracted-assumptions panel

## M2 — Baseline digital twin + synthetic population
- [x] Generate ≥5k numerical micro-agents (origin/dest, income, car access, price sensitivity) — SPEC §6
- [ ] Baseline (World A) metrics: traffic, mode share, emissions proxy, transit demand
- [ ] `GET /baseline` returns baseline metric time series

## M3 — Policy simulation (World B) + time machine
- [ ] Mode-choice + traffic model applying congestion charge/pedestrianisation — SPEC §7.5/§7.7
- [ ] Timeline checkpoints T0,1m,5m,1y,5y,10y with widening uncertainty bands — SPEC §9/§24
- [ ] `POST /simulate` returns Δ(World B − World A) outcome distributions + event ledger (§10)

## M4 — 3D map view
- [ ] MapLibre + deck.gl city render: zones, traffic flow, transit demand, support heatmap
- [ ] Timeline scrubber wired to `/simulate` results; dashboard tiles (traffic/CO₂/transit/equity/support)

## M5 — Model Parliament + amendment loop
- [ ] Agents: Government, Opposition, Equity, Economist, Devil's Advocate (SPEC §11/§12)
- [ ] Opposition proposes 1 amendment; "Apply amendment + re-simulate" recomputes metrics
- [ ] Failure Mode Register from Devil's Advocate (§12)

## M6 — Public reaction + simulated media
- [ ] Cohort support distribution by income/geography (SPEC §13)
- [ ] Simulated media scenarios at Month 5 & Year 2, clearly labelled SIMULATED (§15), driven only by event ledger

## M7 — Evidence drawer + polish
- [ ] Click any metric → provenance/assumptions/confidence trace (SPEC §26)
- [ ] Killer-demo script pass (SPEC §29); deploy or record demo

## Guardrails (apply throughout — SPEC §34)
- LLMs never generate core numeric effects
- Every metric tagged Observed/Estimated/Simulated/Generated + uncertainty
- Long-run uncertainty widens; generated media labelled synthetic
