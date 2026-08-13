"""Optional LLM prose for parliament speeches — with a deterministic fallback.

The LLM is used **only** to turn a persona's already-computed, evidence-grounded
argument points into fluent prose (SPEC §34: language, never numbers). It is
instructed to preserve every figure verbatim and invent nothing. On any failure —
no key, network error, provider mismatch — :class:`ParliamentLLMUnavailable` is
raised and the caller renders the points with a deterministic template instead,
so ``POST /parliament/debate`` always returns.
"""

from __future__ import annotations

import httpx

from ..config import settings


class ParliamentLLMUnavailable(RuntimeError):
    """Raised when the LLM speech path cannot be used; triggers template fallback."""


_SYSTEM_PROMPT = (
    "You are a speechwriter for a parliamentary debate on urban policy. You will be "
    "given a speaker, their role and stance, and a list of evidence-grounded points "
    "that already contain the only permitted facts and numbers. Rewrite them as a "
    "short, natural first-person speech (3-5 sentences). Rules: preserve every number "
    "and named figure EXACTLY; do not add any new statistic, outcome, or claim; do "
    "not invent quotes or named people. Return prose only."
)


def _build_prompt(persona: str, role: str, stance: str, points: list[str]) -> str:
    joined = "\n".join(f"- {p}" for p in points)
    return (
        f"Speaker: {persona} ({role})\n"
        f"Stance: {stance}\n"
        f"Evidence-grounded points:\n{joined}\n\n"
        f"Write {persona}'s speech."
    )


def _call_anthropic(prompt: str) -> str:
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "max_tokens": 512,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    url = settings.llm_base_url.rstrip("/") + "/v1/messages"
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_s)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ParliamentLLMUnavailable(f"LLM request failed: {exc}") from exc
    data = resp.json()
    try:
        blocks = data["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, TypeError) as exc:
        raise ParliamentLLMUnavailable(f"Unexpected LLM response shape: {exc}") from exc
    if not text.strip():
        raise ParliamentLLMUnavailable("LLM returned empty speech.")
    return text.strip()


def generate_speech(persona: str, role: str, stance: str, points: list[str]) -> str:
    """Return LLM prose for the argument, or raise :class:`ParliamentLLMUnavailable`."""
    if not settings.llm_enabled:
        raise ParliamentLLMUnavailable("No LLM API key configured.")
    if settings.llm_provider != "anthropic":
        raise ParliamentLLMUnavailable(f"Unsupported LLM provider: {settings.llm_provider!r}.")
    return _call_anthropic(_build_prompt(persona, role, stance, points))


def template_speech(headline: str, points: list[str]) -> str:
    """Deterministic prose fallback: headline + joined points (no LLM)."""
    body = " ".join(p.rstrip(".") + "." for p in points)
    return f"{headline.rstrip('.')}. {body}".strip()
