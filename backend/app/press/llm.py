"""Optional LLM prose polish for press-conference lines — deterministic fallback.

The LLM only rewrites already-composed, evidence-grounded text into more natural
speech (SPEC §34: language, never numbers). It is instructed to preserve every
figure verbatim and add nothing. On any failure (no key, wrong provider, network,
empty response) :class:`PressLLMUnavailable` is raised and the caller keeps the
deterministic template text, so the endpoint always returns.
"""

from __future__ import annotations

import httpx

from ..config import settings


class PressLLMUnavailable(RuntimeError):
    """Raised when the LLM polish path cannot be used; triggers template fallback."""


_SYSTEM_PROMPT = (
    "You rewrite lines from a simulated government press conference into natural "
    "spoken English. You are given the speaker context and a draft line that "
    "already contains the only permitted facts and numbers. Rules: preserve every "
    "number and figure EXACTLY; add no new statistic, claim, quote or named person; "
    "keep it to 1-3 sentences. Return prose only."
)


def _call_anthropic(context: str, draft: str) -> str:
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    prompt = f"Speaker context: {context}\nDraft line:\n{draft}\n\nRewrite it."
    payload = {
        "model": settings.llm_model,
        "max_tokens": 400,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    url = settings.llm_base_url.rstrip("/") + "/v1/messages"
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_s)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise PressLLMUnavailable(f"LLM request failed: {exc}") from exc
    data = resp.json()
    try:
        blocks = data["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, TypeError) as exc:
        raise PressLLMUnavailable(f"Unexpected LLM response shape: {exc}") from exc
    if not text.strip():
        raise PressLLMUnavailable("LLM returned empty prose.")
    return text.strip()


def polish_prose(context: str, draft: str) -> str:
    """Return LLM-polished prose, or raise :class:`PressLLMUnavailable`."""
    if not settings.llm_enabled:
        raise PressLLMUnavailable("No LLM API key configured.")
    if settings.llm_provider != "anthropic":
        raise PressLLMUnavailable(f"Unsupported LLM provider: {settings.llm_provider!r}.")
    return _call_anthropic(context, draft)
