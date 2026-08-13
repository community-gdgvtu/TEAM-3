"""Data Fabric endpoint (SPEC §4).

``GET /data-fabric`` returns the dataset ingestion & provenance manifest: every
dataset the engine reads, described with the full SPEC §4 metadata record built
live from the file bytes (record counts, variable lists, missingness and a
content-hash revision all computed on disk), plus the supported-format contract
and the harmonisation-pipeline lineage. It is the dataset-level answer to
"where did every number ultimately come from?" — complementing the metric-level
``/evidence`` trace (§26), the model catalogue ``/registry`` (§33) and the
per-run ``/reproduce`` envelope (§32). Deterministic, no LLM.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..datafabric.model import build_data_fabric
from ..datafabric.schema import DataFabric

router = APIRouter(prefix="/data-fabric", tags=["data-fabric"])


@router.get("", response_model=DataFabric, summary="Data ingestion & provenance fabric (SPEC §4)")
def data_fabric() -> DataFabric:
    """Return the full §4 dataset catalogue, format support and harmonisation lineage."""
    return build_data_fabric()
