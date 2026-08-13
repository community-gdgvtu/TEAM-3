# PROGRESS — UI track (frontend)

Dated notes, newest at the bottom. One line per shipped item.

- 2026-08-13 — M4.1: Installed MapLibre GL + deck.gl (+ react-map-gl). Rendered the
  Meridia 3D world: extruded zone choropleth (Residents/Jobs/Job-density switcher),
  road network with cordon-crossing links highlighted, and the CBD cordon polygon.
  Tile-free MapLibre base (no API key, offline), deck.gl overlay via MapboxOverlay,
  hover tooltips, legend, and a "Synthetic" provenance stamp. Geometry bundled to
  `frontend/public/city/` from `data/city/` (loader prefers `NEXT_PUBLIC_CITY_BASE_URL`
  if the backend later serves `/city`). `tsc --noEmit` + `next build` clean.
