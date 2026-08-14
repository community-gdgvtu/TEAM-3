"""Guards the judge-runnable demo script (`scripts/demo.py`).

The demo drives the full `POST /run` pipeline in-process and prints a §29
narrative plus a §34 guardrail audit, returning a non-zero exit code if any
guardrail fails. These tests pin that it stays runnable and that its audit
agrees with the live engine — so the one-command demo can't silently rot as the
backend evolves.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEMO_PATH = os.path.join(_ROOT, "scripts", "demo.py")


def _load_demo():
    spec = importlib.util.spec_from_file_location("urban_demo", _DEMO_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_script_present():
    assert os.path.isfile(_DEMO_PATH), "scripts/demo.py should exist"


def test_demo_runs_and_passes_guardrail_audit(capsys):
    demo = _load_demo()
    exit_code = demo.run([])  # default policy, default horizon
    out = capsys.readouterr().out
    # Exit 0 means every §34 guardrail held on the composed payload.
    assert exit_code == 0, f"demo guardrail audit failed:\n{out}"
    # The narrative sections a judge expects are all rendered.
    for marker in ("Headline dashboard", "Model parliament", "Proposed amendment", "guardrail audit"):
        assert marker in out, f"missing section '{marker}' in demo output"
    # And the audit's positive lines fired.
    assert "guardrails hold" in out


def test_demo_json_mode_is_valid_payload(capsys):
    import json

    demo = _load_demo()
    exit_code = demo.run(["--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    # Must be the real /run payload with all composed sections.
    for key in ("policy_id", "headline", "simulation", "public", "parliament", "amendment", "media"):
        assert key in payload, f"/run payload missing '{key}'"


@pytest.mark.parametrize("horizon", [12.0, 60.0])
def test_demo_alternate_horizons_hold_guardrails(horizon, capsys):
    demo = _load_demo()
    exit_code = demo.run(["--horizon", str(horizon)])
    capsys.readouterr()
    assert exit_code == 0, f"guardrails failed at horizon={horizon}"
