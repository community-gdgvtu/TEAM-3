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
- [ ] Simulated press feed: archetype headlines at Month 5 and Year 2, each visibly stamped SIMULATED

## M7 — Evidence drawer + polish (SPEC §26/§27)
- [ ] Click any dashboard metric → evidence drawer showing the provenance trace, assumptions, confidence (from the backend evidence endpoint)
- [ ] Assemble the main screen layout per SPEC §27 (3D world + outcomes panel + timeline + [Parliament][Public][Press][Red Team] tabs) and wire the 60-second demo flow (SPEC §29)
- [ ] Visual polish: consistent theme, loading/empty/error states, mobile-safe
