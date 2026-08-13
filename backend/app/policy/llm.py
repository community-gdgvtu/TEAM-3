"""Optional LLM path for the policy compiler.

When an API key is configured the compiler asks an LLM to structure the policy
text into the DSL. The LLM is used **only for language understanding** — mapping
words to schema fields — never to invent numeric simulation effects (SPEC §34).
Its output is strictly validated against :class:`PolicyDSL`; any deviation, a
missing key, or a network/credential failure raises :class:`LLMUnavailable` and
the caller falls back to the deterministic rule-based parser.

Currently implements the Anthropic Messages API (the project default). Adding
another provider is a matter of another ``_call_*`` branch; the rest of the
pipeline is provider-agnostic.
"""

from __future__ import annotations

import json

import httpx

from ..config import settings
from .dsl import Assumption, PolicyDSL


class LLMUnavailable(RuntimeError):
    """Raised when the LLM path cannot produce a valid DSL for any reason."""


_SYSTEM_PROMPT = (
    "You are a policy compiler. Convert the user's natural-language urban policy "
    "into a strict JSON object matching the provided schema. Extract ONLY what the "
    "text supports; do not invent charge amounts, dates, or effects. You are "
    "structuring language, not simulating outcomes. Return JSON only, no prose."
)


def _schema_hint() -> str:
    return json.dumps(PolicyDSL.model_json_schema(), separators=(",", ":"))


def _build_prompt(text: str, jurisdiction: str | None) -> str:
    parts = [
        "Policy text:",
        text.strip(),
        "",
        "Target JSON schema (PolicyDSL):",
        _schema_hint(),
        "",
        "Rules:",
        "- Use null / omit fields not present in the text.",
        "- revenue_allocation fractions must sum to ~1.0.",
        "- intervention.type must be one of the schema enum values.",
        "- Dates as ISO YYYY-MM-DD; times as HH:MM 24h.",
    ]
    if jurisdiction:
        parts.append(f"- jurisdiction should be: {jurisdiction}")
    parts.append("")
    parts.append("Return a single JSON object for PolicyDSL.")
    return "\n".join(parts)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown fences if the model wrapped the JSON.
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMUnavailable("LLM response contained no JSON object.")
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMUnavailable(f"LLM returned invalid JSON: {exc}") from exc


def _call_anthropic(prompt: str) -> str:
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "max_tokens": 1024,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    url = settings.llm_base_url.rstrip("/") + "/v1/messages"
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_s)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMUnavailable(f"LLM request failed: {exc}") from exc
    data = resp.json()
    try:
        blocks = data["content"]
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, TypeError) as exc:
        raise LLMUnavailable(f"Unexpected LLM response shape: {exc}") from exc


def compile_with_llm(
    text: str, jurisdiction: str | None = None
) -> tuple[PolicyDSL, list[Assumption]]:
    """Structure ``text`` into a validated :class:`PolicyDSL` via the LLM.

    Raises :class:`LLMUnavailable` if disabled or on any failure so the compiler
    can fall back deterministically.
    """
    if not settings.llm_enabled:
        raise LLMUnavailable("No LLM API key configured.")
    if settings.llm_provider != "anthropic":
        raise LLMUnavailable(f"Unsupported LLM provider: {settings.llm_provider!r}.")

    prompt = _build_prompt(text, jurisdiction)
    raw = _call_anthropic(prompt)
    obj = _extract_json(raw)
    try:
        policy = PolicyDSL.model_validate(obj)
    except Exception as exc:  # pydantic ValidationError et al.
        raise LLMUnavailable(f"LLM output failed schema validation: {exc}") from exc

    if jurisdiction:
        policy.jurisdiction = jurisdiction.lower()

    # The LLM read the whole text at once, so we cannot cheaply attribute each
    # field to a verbatim span. Mark fields that carry a value as LLM-extracted
    # (medium-high confidence) and empty ones as defaults — still fully visible
    # for human correction (SPEC §3).
    assumptions = _assumptions_from_policy(policy)
    return policy, assumptions


def _assumptions_from_policy(policy: PolicyDSL) -> list[Assumption]:
    out: list[Assumption] = []

    def add(field: str, value: object, has_value: bool, rationale: str) -> None:
        out.append(
            Assumption(
                field=field,
                value=value,
                source="inferred" if has_value else "default",
                confidence=0.75 if has_value else 0.3,
                rationale=rationale,
            )
        )

    iv = policy.intervention
    add("intervention.type", iv.type.value, iv.type.value != "other", "LLM-classified intervention.")
    add("intervention.amount", iv.amount, iv.amount is not None, "LLM-extracted charge amount.")
    add("intervention.currency", iv.currency, iv.amount is not None, "LLM-extracted currency.")
    add("intervention.active_hours", iv.active_hours.model_dump(), True, "LLM-extracted active window.")
    add("intervention.implementation_date", iv.implementation_date,
        iv.implementation_date is not None, "LLM-extracted start date.")
    add("intervention.geographic_zone", iv.geographic_zone, True, "LLM-mapped geographic zone.")
    add("exemptions", policy.exemptions, bool(policy.exemptions), "LLM-extracted exemptions.")
    add("revenue_allocation", policy.revenue_allocation.model_dump(),
        policy.revenue_allocation.public_transport > 0, "LLM-extracted revenue split.")
    add("stated_objectives", policy.stated_objectives.model_dump(), True, "LLM-inferred objectives.")
    if policy.constraints.max_low_income_burden_increase_pct is not None:
        add("constraints.max_low_income_burden_increase_pct",
            policy.constraints.max_low_income_burden_increase_pct, True,
            "LLM-extracted equity constraint.")
    return out
