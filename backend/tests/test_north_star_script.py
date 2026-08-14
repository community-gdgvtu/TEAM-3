"""Guards the North-Star runner script (`scripts/north_star.py`).

The runner drives `POST /north-star` in-process and prints the §37 minister's
answer plus a §34 guardrail audit, returning a non-zero exit code if any
guardrail fails. These tests pin that it stays runnable and that its audit
agrees with the live engine — so the one-command North-Star experience can't
silently rot as the backend evolves.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT_PATH = os.path.join(_ROOT, "scripts", "north_star.py")


def _load():
    spec = importlib.util.spec_from_file_location("urban_north_star", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_present():
    assert os.path.isfile(_SCRIPT_PATH), "scripts/north_star.py should exist"


def test_runs_and_passes_guardrail_audit(capsys):
    module = _load()
    exit_code = module.run([])  # default policy, default horizon
    out = capsys.readouterr().out
    assert exit_code == 0, f"north-star guardrail audit failed:\n{out}"
    for marker in ("North-Star answer", "The answer", "Backing figures", "guardrail audit"):
        assert marker in out, f"missing section '{marker}' in output"
    # All 15 §37 lines render.
    for order in range(1, 16):
        assert f"{order:>2}. " in out or f"{order}. " in out
    assert "honours the SPEC §34 guardrails" in out


def test_json_mode_is_valid_payload(capsys):
    module = _load()
    exit_code = module.run(["--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    for key in ("policy_id", "sections", "baseline", "analogues", "uncertainty", "media", "evidence"):
        assert key in payload, f"/north-star payload missing '{key}'"
    assert len(payload["sections"]) == 15


@pytest.mark.parametrize("horizon", [12.0, 60.0])
def test_alternate_horizons_hold_guardrails(horizon, capsys):
    module = _load()
    exit_code = module.run(["--horizon", str(horizon)])
    capsys.readouterr()
    assert exit_code == 0, f"guardrails failed at horizon={horizon}"
