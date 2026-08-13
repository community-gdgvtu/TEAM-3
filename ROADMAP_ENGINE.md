# ROADMAP — ENGINE track (backend / simulation)

**This track owns ONLY:** `backend/**`, `data/**`, `scripts/**`, and this file + `PROGRESS_engine.md`.
**Never edit** `frontend/**`, `ROADMAP_UI.md`, `PROGRESS_ui.md`, `README.md`, `ROADMAP.md`, `SPEC.md`, `AGENT_LOOP.md`.
This keeps parallel tracks from colliding on git. Lock file: `.lock-engine`.

Work top-to-bottom. Each run, do as many items as you can finish cleanly (commit+push after
**each** item). Keep the app runnable and tests green at every commit. Respect SPEC §34
(LLMs never generate core numeric effects; tag metrics Observed/Estimated/Simulated/Generated;
label generated media SIMULATED; uncertainty widens with horizon).

## M3 — Policy simulation (World B) + time machine
- [ ] `backend/app/sim/` — apply the compiled Policy DSL to the mode-choice + traffic model: congestion charge raises car generalized cost inside the cordon; pedestrianisation removes car access on cordon links; revenue → bus frequency → transit access/speed improvement. Deterministic, no LLM. (SPEC §7.5/§7.7)
- [ ] Timeline checkpoints (T0,1m,3m,5m,1y,2y,5y,10y): staged adaptation (behaviour substitution short-run, transit capacity ramp funded by revenue mid-run) with confidence bands that widen with horizon (SPEC §9/§24)
- [ ] `POST /simulate` — body = Policy DSL (+ optional shocks/seed); returns World A, World B, Δ(B−A) per metric across checkpoints, tagged Simulated
- [ ] Event ledger (SPEC §10): structured events (e.g. transit capacity exceeded, cordon load drop) with cause/affected/confidence/downstream — this is the shared truth other engines read

## M5 — Parliament + amendment loop (backend)
- [ ] `backend/app/parliament/` agents: Government, Opposition, Equity, Economist, Devil's Advocate. Each produces evidence-grounded arguments that cite `/simulate` metrics + event-ledger entries (LLM for prose only, with a deterministic template fallback when no key). `POST /parliament/debate`
- [ ] Amendment model + `POST /simulate` support for amended DSL (e.g. exempt bottom-30% income): recompute and return Δ vs original policy
- [ ] Devil's Advocate → ranked Failure Mode Register (risk/mechanism/severity/probability/evidence/mitigation), SPEC §12

## M6 — Public reaction + simulated media (backend)
- [ ] Cohort opinion model (income decile × geography × transport mode): material impact + fairness + prior → support distribution (Strong support…Strong oppose), deterministic core (SPEC §13). Expose via `/simulate` or `POST /public`
- [ ] Simulated media generator `POST /media`: reads ONLY event ledger + outcome metrics + opinion state; emits archetype headlines (public-service/business/local/tabloid/etc.), every artifact tagged `SIMULATED — not a real outlet`, no real bylines (SPEC §15)

## M7 — Evidence, uncertainty, credibility (backend)
- [ ] Evidence/provenance trace endpoint: given a metric id, return the causal trace input-data→transform→model→assumptions→result + confidence (SPEC §26)
- [ ] Uncertainty engine: Monte Carlo / parameter sweep over key elasticities → median + 50/80/95 intervals + most-influential-assumption ranking (SPEC §24)
- [ ] Counterfactual comparison endpoint: World A vs B vs amended C in one payload (SPEC §21)

## Stretch (only if all above done)
- [ ] Policy optimiser stub: given objective+constraints, grid-search a few candidate interventions → Pareto set (SPEC §22)
- [ ] Backtesting harness scaffold (SPEC §25)
