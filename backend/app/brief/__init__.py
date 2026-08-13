"""Minister's Brief export (SPEC §27/§28.11/§37) — a Markdown rendering of the
North-Star answer. Computes no number; formats existing deterministic output."""

from __future__ import annotations

from .schema import BriefRequest, BriefResponse
from .service import build_brief

__all__ = ["BriefRequest", "BriefResponse", "build_brief"]
