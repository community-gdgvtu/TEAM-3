"""Guards the capability-map runner script (`scripts/capabilities.py`).

The runner drives `GET /capabilities` in-process, prints every route grouped by
functional area, and runs a consistency audit (Observed, catalogue reconciles
with the live surface, tags valid, byte-identical on repeat, keyless examples
served), returning a non-zero exit code on failure. These tests pin that it
stays runnable and its audit agrees with the live engine.
"""

from __future__ import annotations

import importlib.util
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT_PATH = os.path.join(_ROOT, "scripts", "capabilities.py")


def _load():
    spec = importlib.util.spec_from_file_location("urban_capabilities_cli", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_present():
    assert os.path.isfile(_SCRIPT_PATH), "scripts/capabilities.py should exist"


def test_runs_and_passes_consistency_audit(capsys):
    module = _load()
    exit_code = module.run([])
    out = capsys.readouterr().out
    assert exit_code == 0, f"capability-map consistency audit failed:\n{out}"
    for marker in ("engine capability map", "consistency checks", "SPEC sections"):
        assert marker in out, f"missing section '{marker}' in output"
    # A couple of load-bearing areas are printed.
    assert "Hybrid forecast layers" in out
    assert "Composed answers & export" in out
    assert "consistent with the live surface" in out


def test_json_mode_is_valid_manifest(capsys):
    module = _load()
    exit_code = module.run(["--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    for key in ("provenance", "groups", "keyless_examples", "undocumented_routes", "counts"):
        assert key in payload, f"/capabilities payload missing '{key}'"
    assert payload["undocumented_routes"] == []
    assert payload["phantom_cards"] == []
    assert payload["counts"]["routes"] > 0


def test_area_filter_selects_one_area(capsys):
    module = _load()
    exit_code = module.run(["--area", "Governance agents"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "/parliament/debate" in out
    # An endpoint from a different area is not printed under this filter.
    assert "/timeseries" not in out


def test_unknown_area_fails_with_valid_list(capsys):
    module = _load()
    exit_code = module.run(["--area", "not-a-real-area"])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "Valid areas" in out
