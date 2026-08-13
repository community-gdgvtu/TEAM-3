"""Policy compiler orchestration: LLM path with deterministic fallback.

Strategy (AGENT_LOOP.md): if an LLM key is configured, try the LLM path first;
on *any* failure fall back to the rule-based parser so the endpoint never breaks.
With no key, go straight to rules. Either way the caller gets a validated
:class:`PolicyDSL` and a list of reviewable assumptions.
"""

from __future__ import annotations

from .dsl import CompileResponse
from .llm import LLMUnavailable, compile_with_llm
from .rules import parse_policy


def compile_policy(text: str, jurisdiction: str | None = None) -> CompileResponse:
    """Compile ``text`` into a :class:`CompileResponse`."""
    warnings: list[str] = []

    try:
        policy, assumptions = compile_with_llm(text, jurisdiction)
        method = "llm"
    except LLMUnavailable as exc:
        # Expected whenever no key is set; only surface as a warning if a key was
        # configured but the call failed (a real degradation the user should see).
        from ..config import settings

        if settings.llm_enabled:
            warnings.append(f"LLM path unavailable, used rule-based fallback: {exc}")
        policy, assumptions = parse_policy(text, jurisdiction)
        method = "rule_based"

    # Sanity guardrail: revenue allocation should roughly sum to 1.
    alloc = policy.revenue_allocation
    total = alloc.public_transport + alloc.general_fund + alloc.active_travel + alloc.other
    if abs(total - 1.0) > 0.02:
        warnings.append(
            f"Revenue allocation sums to {total:.2f}, not 1.0 — review the split."
        )

    return CompileResponse(
        policy=policy,
        assumptions=assumptions,
        method=method,
        provenance="Generated",
        warnings=warnings,
    )
