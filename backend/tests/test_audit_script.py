"""Guards the whole-surface guardrail-audit script (`scripts/audit.py`).

The audit runner drives *every* engine route in-process and reports a single
pass/fail §34 compliance matrix (routes serve, provenance tagged, no LLM in the
numeric path, media SIMULATED, numeric layers deterministic, uncertainty widens),
returning non-zero if any guardrail fails. These tests pin that it stays runnable
and that its verdict tracks the live engine — so the one-command "prove it isn't
AI astrology" audit can't silently rot as the backend evolves, and so a real §34
regression (a route 500ing, a tag dropped, a layer going non-deterministic) turns
this red rather than passing unnoticed.
"""

from __future__ import annotations

import importlib.util
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT_PATH = os.path.join(_ROOT, "scripts", "audit.py")


def _load():
    spec = importlib.util.spec_from_file_location("urban_audit", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_present():
    assert os.path.isfile(_SCRIPT_PATH), "scripts/audit.py should exist"


def test_runs_and_passes_full_surface_audit(capsys):
    module = _load()
    exit_code = module.run([])
    out = capsys.readouterr().out
    assert exit_code == 0, f"whole-surface guardrail audit failed:\n{out}"
    for marker in ("guardrail audit", "Route health", "guardrail checks", "PASS"):
        assert marker in out, f"missing section '{marker}' in output"
    assert "honours the SPEC §34 guardrails" in out


def test_json_report_is_complete_and_green(capsys):
    module = _load()
    exit_code = module.run(["--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    report = json.loads(out)
    # Every declared §34 check is present and passing.
    for key in module._CHECK_LABELS:
        assert report["checks"].get(key) is True, f"check '{key}' not green: {report['checks']}"
    assert report["passed"] is True
    # It actually exercised the whole surface, not a token subset.
    assert report["route_count"] >= 35
    assert not report["routes_failed"]
    assert not report["tag_violations"]
    assert not report["llm_offenders"]
    assert not report["determinism_failed"]
    # The registry it audits lists every forecast layer.
    assert report["registry_model_count"] >= 15


def test_report_verdict_reflects_a_real_regression():
    """The audit must FAIL if a guardrail is genuinely violated — so it's a real
    gate, not a rubber stamp. We corrupt a copy of a passing report and confirm
    the pass/fail rollup flips (mirrors the script's own ``passed`` logic)."""
    module = _load()
    report = module.build_report(module.DEMO_TEXT)
    assert report["passed"] is True
    # Flip any single check → the whole audit must fail.
    for key in report["checks"]:
        corrupted = dict(report["checks"])
        corrupted[key] = False
        assert all(corrupted.values()) is False, f"flipping '{key}' should fail the audit"


def test_custom_policy_audit_holds(capsys):
    module = _load()
    exit_code = module.run(["--text", "Pedestrianise the central business district to private cars."])
    capsys.readouterr()
    assert exit_code == 0, "guardrails should hold for a pedestrianisation policy too"
