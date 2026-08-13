# PROGRESS — UI track (frontend)

Dated notes, newest at the bottom. One line per shipped item.

- 2026-08-13 — M4.1: Installed MapLibre GL + deck.gl (+ react-map-gl). Rendered the
  Meridia 3D world: extruded zone choropleth (Residents/Jobs/Job-density switcher),
  road network with cordon-crossing links highlighted, and the CBD cordon polygon.
  Tile-free MapLibre base (no API key, offline), deck.gl overlay via MapboxOverlay,
  hover tooltips, legend, and a "Synthetic" provenance stamp. Geometry bundled to
  `frontend/public/city/` from `data/city/` (loader prefers `NEXT_PUBLIC_CITY_BASE_URL`
  if the backend later serves `/city`). `tsc --noEmit` + `next build` clean.
- 2026-08-13 — M4.2: Added switchable deck.gl overlays — Traffic flow, Transit demand,
  Support/opposition. Transit heatmap is derived from the real synthetic OD matrix
  (tagged Synthetic, world input); traffic (corridor-load index from link capacity)
  and support (distance-from-CBD gradient) are clearly stamped Placeholder until
  `/simulate` is live (SPEC §34). Each overlay shows a provenance chip + honesty
  caption + legend. Pure metadata split into overlayMeta.ts to keep the WebGL stack
  out of SSR. OD matrix lazy-loaded (~0.4 MB) only when transit is selected.
  `tsc --noEmit` + `next build` clean.
