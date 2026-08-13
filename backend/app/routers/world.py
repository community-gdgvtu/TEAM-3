"""Baseline World Model endpoint (SPEC §5 / §28.2).

``GET /world`` returns World A's structural composition — the browsable digital
twin the demo renders (§28.2) — organised as the six SPEC §5 layers. Optional
``?layers=`` selects the smallest sufficient subset (SPEC §5). Deterministic,
no LLM (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..world import ALL_LAYERS, WorldModel, compose_world

router = APIRouter(prefix="/world", tags=["world"])


@router.get("", response_model=WorldModel, summary="Baseline World Model (SPEC §5 / §28.2)")
def get_world(
    layers: str | None = Query(
        default=None,
        description=(
            "Comma-separated subset of layers to return "
            f"({', '.join(ALL_LAYERS)}). Omit for all six (SPEC §5 smallest-"
            "sufficient selection)."
        ),
    ),
) -> WorldModel:
    """Compose and return the deterministic World-A twin.

    Every number is read from the synthetic dataset or the baseline ABM and
    tagged Simulated/Observed/Estimated per the SPEC §8 table; no LLM produces
    any figure (SPEC §34). Repeated calls are byte-identical (cached).
    """
    selected: tuple[str, ...] | None = None
    if layers is not None:
        requested = [l.strip().lower() for l in layers.split(",") if l.strip()]
        unknown = [l for l in requested if l not in ALL_LAYERS]
        if unknown:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Unknown layer(s): {', '.join(unknown)}. "
                    f"Valid layers: {', '.join(ALL_LAYERS)}."
                ),
            )
        if requested:
            selected = tuple(requested)
    return compose_world(selected)
