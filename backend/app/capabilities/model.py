"""Build the capability manifest, reconciled live against the app's routes.

The manifest's route list is derived from the running FastAPI app (so methods
and existence are read live, never hand-copied), joined to the curated catalogue
for the SPEC mapping / summaries. Any live route without a card surfaces in
``undocumented_routes`` and any card for a missing route in ``phantom_cards`` —
both MUST be empty, so the catalogue cannot silently fall behind the surface.
"""

from __future__ import annotations

from fastapi import FastAPI

from ..config import settings
from .catalogue import AREA_META, ENDPOINTS, INFRA_PATHS, _KEYLESS_COMPANION
from .schema import CapabilityGroup, CapabilityManifest, EndpointCard

_HTTP_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def live_route_methods(app: FastAPI) -> dict[str, list[str]]:
    """Map each served product path → sorted HTTP methods (infra excluded)."""
    out: dict[str, set[str]] = {}
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path or path in INFRA_PATHS:
            continue
        wanted = {m for m in methods if m in _HTTP_METHODS}
        if not wanted:
            continue
        out.setdefault(path, set()).update(wanted)
    return {p: sorted(m) for p, m in out.items()}


def build_capabilities(app: FastAPI) -> CapabilityManifest:
    """Compose the capability manifest for ``app``."""
    live = live_route_methods(app)
    cards_by_path = {row[0]: row for row in ENDPOINTS}

    # Build a card per catalogued route that actually exists live.
    endpoints: dict[str, EndpointCard] = {}
    for path, methods in live.items():
        row = cards_by_path.get(path)
        if row is None:
            continue  # undocumented — surfaced below, not silently carded
        _, area, spec_sections, summary, produces_numbers, output_tag, _ = row
        endpoints[path] = EndpointCard(
            path=path,
            methods=methods,
            area=area,
            spec_sections=list(spec_sections),
            summary=summary,
            needs_body="POST" in methods or "PUT" in methods or "PATCH" in methods,
            keyless_example=_KEYLESS_COMPANION.get(path),
            produces_numbers=produces_numbers,
            output_tag=output_tag,
        )

    # Group by the curated area ordering; areas keep their SPEC/summary metadata.
    groups: list[CapabilityGroup] = []
    for area, spec_sections, summary in AREA_META:
        members = [c for c in endpoints.values() if c.area == area]
        members.sort(key=lambda c: c.path)
        if members:
            groups.append(
                CapabilityGroup(
                    area=area,
                    spec_sections=list(spec_sections),
                    summary=summary,
                    endpoints=members,
                )
            )

    undocumented = sorted(p for p in live if p not in cards_by_path)
    phantom = sorted(p for p in cards_by_path if p not in live)
    # Keyless = a no-body GET a judge can hit directly. Parameterised paths
    # (``/scenarios/{scenario_id}``) need an argument, so they are not keyless.
    keyless = sorted(
        c.path
        for c in endpoints.values()
        if "GET" in c.methods and "{" not in c.path and c.path not in ("/", "/health")
    )

    get_paths = [c.path for c in endpoints.values() if "GET" in c.methods]
    post_paths = [c.path for c in endpoints.values() if "POST" in c.methods]

    return CapabilityManifest(
        app_version=settings.version,
        groups=groups,
        keyless_examples=keyless,
        undocumented_routes=undocumented,
        phantom_cards=phantom,
        counts={
            "routes": len(endpoints),
            "areas": len(groups),
            "get": len(get_paths),
            "post": len(post_paths),
            "keyless_examples": len(keyless),
            "spec_sections": len(
                sorted({s for c in endpoints.values() for s in c.spec_sections})
            ),
        },
    )
