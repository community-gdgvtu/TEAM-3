"""Health / readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    llm_enabled: bool


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    """Report service liveness and coarse configuration state.

    ``llm_enabled`` reflects whether an LLM key is configured. When ``False``,
    AI-dependent endpoints fall back to rule-based behaviour (AGENT_LOOP.md).
    """
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        llm_enabled=settings.llm_enabled,
    )
