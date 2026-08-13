"""Service capability manifest endpoint (SPEC §27/§33 transparency).

``GET /capabilities`` returns the machine-readable "front door": every HTTP route
the engine serves, mapped to its SPEC section, functional area, provenance class
and keyless-example companion, reconciled live against the running app's routes.
Deterministic, no LLM, Observed about the service.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..capabilities.model import build_capabilities
from ..capabilities.schema import CapabilityManifest

router = APIRouter(tags=["system"])


@router.get(
    "/capabilities",
    response_model=CapabilityManifest,
    summary="Service capability manifest (SPEC §27/§33)",
)
def capabilities(request: Request) -> CapabilityManifest:
    """Return the full route-surface manifest, mapped to SPEC sections."""
    return build_capabilities(request.app)
