"""Guards the robustness runner script (`scripts/robustness.py`).

The runner drives `POST /robustness` in-process, prints the decision table + the
pick each criterion makes, and runs a §34 guardrail audit (provenance-tagged,
regret well-formed, payoffs equal the stress-core Δ(B−A), byte-identical on
repeat, no long-horizon over-claim), returning a non-zero exit code on failure.
These tests pin that it stays runnable and its audit agrees with the live engine.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT_PATH = os.path.join(_ROOT, "scripts", "robustness.py")


def _load():
    spec = importlib.util.spec_from_file_location("urban_robustness_cli", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_present():
    assert os.path.isfile(_SCRIPT_PATH), "scripts/robustness.py should exist"


def test_runs_and_passes_guardrail_audit(capsys):
    module = _load()
    exit_code = module.run([])  # default objective + horizon
    out = capsys.readouterr().out
    assert exit_code == 0, f"robustness guardrail audit failed:\n{out}"
    for marker in ("robustness / regret ranking", "Decision table", "criterion picks", "guardrail audit"):
        assert marker in out, f"missing section '{marker}' in output"
    # Every decision criterion is named.
    for crit in ("nominal", "maximin", "minimax-regret", "laplace", "most-robust"):
        assert crit in out
    assert "honours the SPEC §34 guardrails" in out


def test_json_mode_is_valid_payload(capsys):
    module = _load()
    exit_code = module.run(["--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    for key in ("objective_key", "candidates", "picks", "headline", "states"):
        assert key in payload, f"/robustness payload missing '{key}'"
    assert len(payload["candidates"]) == 3
    assert payload["states"][0] == "baseline"


@pytest.mark.parametrize("horizon", [12.0, 60.0])
def test_alternate_horizons_hold_guardrails(horizon, capsys):
    module = _load()
    exit_code = module.run(["--horizon", str(horizon)])
    out = capsys.readouterr().out
    assert exit_code == 0, f"guardrail audit failed at horizon {horizon}:\n{out}"


def test_alternate_objective(capsys):
    module = _load()
    exit_code = module.run(["--objective", "transit.daily_transit_trips"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "daily transit trips" in out
