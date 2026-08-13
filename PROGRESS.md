# PROGRESS

Dated one-line notes from the autonomous dev loop. Newest at the bottom.

- 2026-08-13 — M0: FastAPI backend skeleton (`backend/app/`) with `/` + `/health` (reports version + `llm_enabled`), CORS from env, settings via pydantic-settings, `requirements.txt`, `.env.example`, and pytest smoke tests (3 passing). Next: Next.js frontend skeleton calling `/health`.
- 2026-08-13 — M0: Next.js 14 (App Router) + TS frontend skeleton (`frontend/`). Landing page with SPEC-§34 tagging blurb + client `HealthStatus` component that fetches backend `/health` via `NEXT_PUBLIC_API_BASE_URL`; typed `lib/api.ts`, dark theme CSS, `.eslintrc`, `.env.local.example`, README. Verified: `npm run typecheck` + `next build` clean, and live smoke test (backend on :8010 `/health` ok, CORS preflight from :3000 → 200, prod frontend serves landing markers). Next: shared synthetic city grid dataset in `data/`.
