"""Rogue-LLM injection guard — SPEC §34 guardrail #1: *LLMs never generate core
numeric effects.*

Every other test in the suite runs with no LLM key, i.e. exclusively through the
deterministic template fallback. That proves the endpoints *work* without a
model, but it never exercises the LLM-enabled path — so nothing currently proves
that an **enabled** model cannot leak numbers into a response. A refactor that
accidentally parsed figures back out of LLM prose, let the model rewrite an
evidence point / cited ref, or recomputed a tally from generated text would sail
past every existing test.

This guard closes that gap directly. For each prose surface (parliament debate,
press conference) it runs the pipeline twice:

  1. **template** — the honest deterministic path (no LLM);
  2. **rogue** — the LLM seam monkeypatched to a *hostile* model that ignores its
     instructions, discards the evidence, and emits fabricated numbers.

It then asserts the two responses are **byte-identical after stripping only the
free-text prose fields** (and the ``method`` flag). If any fabricated figure, or
any structural change, reaches a numeric/structural field — points, cited refs,
tallies, Δ metrics, stances, moods — the skeletons diverge and this fails. A
companion assertion proves the rogue model *did* change the prose, so the guard
can never pass vacuously.
"""

from __future__ import annotations

import copy

from app.parliament.debate import run_debate
from app.policy.dsl import (
    Constraints,
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.press.conference import run_press_conference

# Leaf keys whose values are LLM-authored prose. We strip them (only when the
# value is a string, so the nested PressExchange.answer *object* is preserved
# while the PressAnswer.answer *string* inside it is removed) together with the
# `method` flag, which legitimately flips 'template' -> 'llm'.
_PROSE_KEYS = {"speech", "opening_statement", "answer", "method"}

# A hostile model would preserve nothing and invent everything. These sentinels
# must never surface in a numeric/structural field.
_ROGUE_TEXT = (
    "Congestion collapses by 999 percent, revenue is 42 trillion credits, and "
    "every one of the 7 personas agrees unanimously. Signed, a rogue model."
)


def _strip_prose(node):
    """Recursively drop LLM-authored string leaves, returning the numeric skeleton."""
    if isinstance(node, dict):
        return {
            k: _strip_prose(v)
            for k, v in node.items()
            if not (k in _PROSE_KEYS and isinstance(v, str))
        }
    if isinstance(node, list):
        return [_strip_prose(v) for v in node]
    return node


def _policy() -> PolicyDSL:
    return PolicyDSL(
        id="policy_llm_invariance",
        intervention=Intervention(
            type=InterventionType.road_pricing,
            amount=12.0,
            currency="local",
            geographic_zone="cbd_polygon",
        ),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
        exemptions=[],
        constraints=Constraints(max_low_income_burden_increase_pct=None),
    )


# --------------------------------------------------------------------------- #
# Parliament debate
# --------------------------------------------------------------------------- #

def test_rogue_llm_cannot_touch_parliament_numbers(monkeypatch) -> None:
    policy = _policy()

    # Honest deterministic path (test env has no key -> template).
    template = run_debate(policy).model_dump()
    assert template["method"] == "template"

    # Enable the LLM gate, then hijack the speech seam with a hostile model.
    monkeypatch.setattr("app.config.settings.llm_api_key", "rogue-key")

    def _rogue_speech(persona, role, stance, points):  # noqa: ANN001
        # Ignore every evidence-grounded point; emit fabricated figures instead.
        return f"{persona}: {_ROGUE_TEXT}"

    monkeypatch.setattr("app.parliament.debate.generate_speech", _rogue_speech)

    rogue = run_debate(policy).model_dump()
    assert rogue["method"] == "llm"  # the rogue path really ran

    # The rogue prose really did change the raw output (guard isn't vacuous)...
    assert rogue != template
    assert any(_ROGUE_TEXT in a["speech"] for a in rogue["arguments"])

    # ...but the numeric/structural skeleton is byte-identical, and no fabricated
    # figure leaked into any non-prose field.
    assert _strip_prose(rogue) == _strip_prose(template)
    for arg in rogue["arguments"]:
        for pt in arg["points"]:
            assert "999" not in pt and "42 trillion" not in pt
    assert rogue["tally"] == template["tally"]
    assert rogue["summary"] == template["summary"]


# --------------------------------------------------------------------------- #
# Press conference
# --------------------------------------------------------------------------- #

def test_rogue_llm_cannot_touch_press_numbers(monkeypatch) -> None:
    policy = _policy()

    template = run_press_conference(policy, use_llm=False).model_dump()
    assert template["method"] == "template"

    def _rogue_polish(context, draft):  # noqa: ANN001
        return _ROGUE_TEXT

    monkeypatch.setattr("app.press.conference.polish_prose", _rogue_polish)

    rogue = run_press_conference(policy, use_llm=True).model_dump()
    assert rogue["method"] == "llm"

    # Rogue prose changed the surface text...
    assert rogue != template
    assert rogue["opening_statement"] == _ROGUE_TEXT
    assert all(ex["answer"]["answer"] == _ROGUE_TEXT for ex in rogue["exchanges"])

    # ...yet cited refs, stances, questions, mood and every other field are intact.
    assert _strip_prose(rogue) == _strip_prose(template)
    for ex, base in zip(rogue["exchanges"], template["exchanges"]):
        assert ex["answer"]["cited_refs"] == base["answer"]["cited_refs"]
        assert ex["answer"]["stance"] == base["answer"]["stance"]
        assert "999" not in " ".join(ex["answer"]["cited_refs"])
    assert rogue["public_mood"] == template["public_mood"]
    assert rogue["opening_refs"] == template["opening_refs"]


def test_prose_stripper_preserves_numeric_leaves() -> None:
    """The skeleton extractor removes prose leaves but keeps nested structure."""
    sample = {
        "method": "llm",
        "opening_statement": "prose",
        "tally": {"support": 3, "oppose": 2},
        "exchanges": [
            {"answer": {"answer": "prose", "stance": "defends", "cited_refs": ["m1"]}}
        ],
    }
    stripped = _strip_prose(copy.deepcopy(sample))
    assert "method" not in stripped
    assert "opening_statement" not in stripped
    assert stripped["tally"] == {"support": 3, "oppose": 2}
    ans = stripped["exchanges"][0]["answer"]
    assert "answer" not in ans  # prose string dropped
    assert ans["stance"] == "defends"  # non-prose sibling kept
    assert ans["cited_refs"] == ["m1"]  # numeric-bearing refs kept
