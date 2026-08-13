# URBAN frontend

Next.js (App Router) + TypeScript UI for the URBAN policy digital twin.

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

## Scripts

- `npm run dev` — dev server
- `npm run build` — production build
- `npm run start` — serve the production build
- `npm run lint` — ESLint (next/core-web-vitals)
- `npm run typecheck` — `tsc --noEmit`

## Config

- `NEXT_PUBLIC_API_BASE_URL` — base URL of the FastAPI backend (browser-reachable).
