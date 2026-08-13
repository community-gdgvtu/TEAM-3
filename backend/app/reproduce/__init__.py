"""Run reproducibility layer (SPEC §32).

Assembles the per-run **reproducibility manifest** behind the "REPRODUCE RUN"
affordance: everything needed to regenerate an identical scenario — dataset
versions, model versions, parameters/assumptions, seed, policy DSL, code
version, and a timestamp — plus a content-addressed ``run_id`` that is stable
for identical inputs and a self-check that the deterministic core reproduces
byte-for-byte. Transparency artifact, not a forecast; deterministic, no LLM
(SPEC §32/§34).
"""

from .manifest import build_manifest
from .schema import ReproManifest

__all__ = ["build_manifest", "ReproManifest"]
