"""Model registry endpoint (SPEC §33).

``GET /registry`` returns the transparency manifest: every forecast layer, its
documented assumptions (read live from the code), the data sources it reads, and
the SPEC §34 guardrails plus how each is enforced. It is the machine-readable
"how do we know these numbers aren't AI astrology?" answer. Deterministic, no LLM.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..registry.model import build_registry
from ..registry.schema import ModelRegistry

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("", response_model=ModelRegistry, summary="Model & assumption registry (SPEC §33)")
def registry() -> ModelRegistry:
    """Return the full model/assumption/guardrail transparency manifest."""
    return build_registry()
