"""Data Fabric — dataset ingestion & provenance layer (SPEC §4).

A first-class, machine-readable catalogue of every dataset the engine reads,
carrying the full SPEC §4 provenance schema (title/publisher/source_url/…/
transformation_history) built *live* from the actual files on disk so it can
never drift from what runs, plus the harmonisation-pipeline lineage and the
mandated ``input data → transformation → model → assumptions → result`` trace.

This is the dataset-level provenance layer. It complements — and does not
duplicate — the metric-level explainability trace (§26, ``/evidence``), the
static model catalogue (§33, ``/registry``) and the per-run reproducibility
envelope (§32, ``/reproduce``). It is Observed about the data itself: a
transparency artifact, not a simulation output. Deterministic, no LLM.
"""

from .model import build_data_fabric
from .schema import DataFabric

__all__ = ["build_data_fabric", "DataFabric"]
