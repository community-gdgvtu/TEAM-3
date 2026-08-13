# AGENT_LOOP.md — Autonomous Development Loop Contract

This project is built by a recurring autonomous agent (a cron job). Each run is a fresh,
isolated session. Follow this contract exactly so progress compounds instead of thrashing.

## Each iteration

1. `cd /home/linux/urban-policy-twin` and run `git pull --rebase` (in case of external changes).
2. Read `ROADMAP.md`. Pick the **first unchecked `[ ]` item**. Do only that one item (or a
   coherent sub-part if it's large). Do not scope-creep into later milestones.
3. Implement it end-to-end so the repo still runs. Small, working, real code — no stubs
   that pretend to work, no fabricated data presented as real.
4. Verify what you built: run the relevant `npm run build`/`pytest`/`uvicorn --help`/lint or a
   quick smoke test. If it doesn't work, fix it before committing.
5. Check the item off in `ROADMAP.md` (`[x]`) and add a one-line note to `PROGRESS.md`
   (create if missing) with date + what changed + any follow-ups discovered.
6. Commit with a clear message and `git push`. One logical change per commit.
7. If the picked item is genuinely blocked (needs a secret, a human decision, or an external
   account), note the blocker in `PROGRESS.md`, skip to the next actionable item, and continue.

## Rules

- **Product guardrails (SPEC §34) are non-negotiable:** LLMs never generate core numeric
  simulation effects; every metric is tagged Observed/Estimated/Simulated/Generated; generated
  media is labelled SIMULATED; long-run uncertainty widens.
- Keep the app runnable at every commit. A working small slice beats a broken big one.
- Don't commit secrets. Use `.env.example` for config; read real keys from the environment.
- Prefer existing libraries over hand-rolled infra.
- If you finish a whole milestone, keep going into the next one.
- Keep commits pushed so progress is visible on GitHub.

## LLM / API keys

The AI layer needs an LLM key at runtime. If none is configured, code paths that need it must
degrade gracefully (rule-based fallback) so the build never blocks. Do not hardcode keys.
