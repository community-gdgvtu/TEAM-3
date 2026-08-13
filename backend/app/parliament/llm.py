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


_QA_SYSTEM_PROMPT = (
    "You are role-playing as a persona in a parliamentary debate on urban policy, "
    "answering a follow-up question from a citizen or journalist. You will be given "
    "your role, stance, a list of evidence-grounded points that already contain the "
    "only permitted facts and numbers, and the question. Answer in first person, "
    "2-4 sentences, in character. Rules: preserve every number EXACTLY as given; do "
    "not invent any new statistic, outcome, or claim not present in the points; if "
    "the question asks about something the points don't cover, say so honestly "
    "instead of guessing. Return prose only."
)


def _build_qa_prompt(
    persona: str, role: str, stance: str, points: list[str], question: str
) -> str:
    joined = "\n".join(f"- {p}" for p in points)
    return (
        f"Speaker: {persona} ({role})\n"
        f"Stance: {stance}\n"
        f"Evidence-grounded points:\n{joined}\n\n"
        f"Question: {question.strip()}\n\n"
        f"Answer as {persona}."
    )


def _call_anthropic(prompt: str, system: str = _SYSTEM_PROMPT) -> str:
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "max_tokens": 512,
        "system": system,
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


def generate_answer(
    persona: str, role: str, stance: str, points: list[str], question: str
) -> str:
    """Return LLM prose answering ``question`` in character, or raise.

    Same guardrail as :func:`generate_speech`: the LLM may only phrase the
    already-computed ``points`` — it is instructed never to add a new figure.
    """
    if not settings.llm_enabled:
        raise ParliamentLLMUnavailable("No LLM API key configured.")
    if settings.llm_provider != "anthropic":
        raise ParliamentLLMUnavailable(f"Unsupported LLM provider: {settings.llm_provider!r}.")
    return _call_anthropic(
        _build_qa_prompt(persona, role, stance, points, question), system=_QA_SYSTEM_PROMPT
    )


def template_answer(headline: str, points: list[str], question: str) -> str:
    """Deterministic fallback answer: the point(s) most relevant to ``question``.

    Simple keyword overlap against words longer than 3 characters — no LLM, so
    the endpoint always answers something grounded in the persona's actual
    evidence, even with no API key configured.
    """
    if not points:
        return headline
    q_words = {w.strip(".,!?\"'").lower() for w in question.split() if len(w) > 3}

    def score(point: str) -> int:
        p_words = {w.strip(".,!?\"'").lower() for w in point.split()}
        return len(q_words & p_words)

    best = max(points, key=score)
    if score(best) == 0:
        return f"{headline.rstrip('.')}. {points[0]}".strip()
    return best
