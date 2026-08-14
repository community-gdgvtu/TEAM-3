"""Tests for the Minister's Brief export ``POST /brief`` (SPEC §27/§28.11/§37).

The brief is a *rendering* of the North-Star answer, so its whole value is
fidelity: it must format the §37 answer without inventing, dropping, or
re-deriving a number. These tests pin the endpoint contract, the fixed §37
structure surviving into the memo, consistency with ``/north-star``,
determinism, the presentation switches, and the §34 guardrails (provenance key,
SIMULATED media, no LLM-in-numbers claim).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)

ALLOWED_TAGS = {"Observed", "Estimated", "Simulated", "Generated"}


def _brief(payload: dict) -> dict:
    r = client.post("/brief", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_example_renders_full_memo() -> None:
    r = client.get("/brief/example")
    assert r.status_code == 200, r.text
    d = r.json()
    md = d["markdown"]
    assert md.startswith("# Minister's Brief")
    assert d["word_count"] == len(md.split())
    assert d["word_count"] > 100
    # The provenance key is printed with all four tags (SPEC §34).
    assert {e["tag"] for e in d["tag_legend"]} == ALLOWED_TAGS
    for tag in ALLOWED_TAGS:
        assert f"**{tag}**" in md
    # Canonical demo policy + a real headline horizon.
    assert d["policy_id"]
    assert d["horizon_label"]


def test_brief_from_text_preserves_section37_order() -> None:
    d = _brief({"text": DEMO_TEXT})
    md = d["markdown"]
    # All 15 §37 lines survive, in order, inside the memo.
    positions = [md.find(f"**{i}. ") for i in range(1, 16)]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions), "§37 lines are out of order in the memo"
    # A headline table and a failure table are present.
    assert "## Executive summary" in md
    assert "| Metric |" in md
    assert "Where it is most likely to fail" in md


def test_brief_is_consistent_with_north_star() -> None:
    """The brief must not invent numbers: its answer == /north-star's answer."""
    payload = {"text": DEMO_TEXT, "seed": 7}
    brief = _brief(payload)
    ns = client.post("/north-star", json=payload)
    assert ns.status_code == 200, ns.text
    ns_d = ns.json()
    # Same policy, same horizon, same headline tiles (byte-for-byte).
    assert brief["policy_id"] == ns_d["policy_id"]
    assert brief["horizon_months"] == ns_d["horizon_months"]
    assert brief["answer"]["median_outcome"] == ns_d["median_outcome"]
    # Every headline value the memo prints comes from that answer.
    for tile in ns_d["median_outcome"]:
        assert tile["label"] in brief["markdown"]


def test_brief_is_deterministic() -> None:
    payload = {"text": DEMO_TEXT, "seed": 3}
    assert _brief(payload)["markdown"] == _brief(payload)["markdown"]


def test_presentation_switches() -> None:
    # include_answer=False drops the heavy structured payload.
    d = _brief({"text": DEMO_TEXT, "include_answer": False})
    assert d["answer"] is None
    assert d["markdown"]  # memo still rendered
    # include_media=False drops the media section from the memo.
    no_media = _brief({"text": DEMO_TEXT, "include_media": False})
    assert "## Simulated media narratives" not in no_media["markdown"]
    with_media = _brief({"text": DEMO_TEXT, "include_media": True})
    assert "## Simulated media narratives" in with_media["markdown"]


def test_guardrails_present_in_memo() -> None:
    md = _brief({"text": DEMO_TEXT})["markdown"]
    # SPEC §34: media labelled SIMULATED and the no-LLM-in-numbers claim stated.
    assert "SIMULATED" in md
    assert "No LLM touches any figure" in md or "no LLM" in md.lower()
    # SPEC §32: reproducibility footer with a seed line.
    assert "Reproducibility & assumptions" in md
    assert "seed" in md.lower()


def test_precompiled_policy_path() -> None:
    """A pre-compiled DSL skips compilation and still renders a brief."""
    comp = client.post("/policy/compile", json={"text": DEMO_TEXT})
    assert comp.status_code == 200, comp.text
    policy = comp.json()["policy"]
    d = _brief({"policy": policy})
    assert d["answer"]["compiled"] is None  # no compile step on the policy path
    assert d["markdown"].startswith("# Minister's Brief")
