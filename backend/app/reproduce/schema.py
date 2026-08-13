"""Pydantic schemas for the run reproducibility manifest (SPEC §32).

SPEC §32 requires that every run store its dataset versions, model versions,
parameters, random seed, prompts, policy DSL, assumptions, code version and
timestamp so a user can click **REPRODUCE RUN** and regenerate the same
scenario. This module is the machine-readable shape of that record.

Nothing here is a simulation output — the manifest *describes* how a Simulated
run is produced and pins the exact inputs, so it is Observed about itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag
from ..policy.dsl import PolicyDSL
from ..registry.schema import AssumptionRecord


class DatasetVersion(BaseModel):
    """One pinned input dataset (SPEC §4/§32).

    ``content_sha256`` is a hash of the file's actual bytes, so any change to the
    generated world state changes the fingerprint (and therefore the ``run_id``).
    """

    id: str = Field(description="Stable key, e.g. 'city_grid' or 'population'.")
    name: str
    provenance: MetricTag = Field(
        MetricTag.observed,
        description="Datasets are Observed inputs (here: synthetic-but-fixed world state).",
    )
    kind: str = Field(default="synthetic", description="'synthetic' | 'legacy' | 'live'.")
    generated_by: str = Field(default="", description="Script that produced the dataset.")
    seed: object = Field(default=None, description="Generation seed, if recorded.")
    path: str = Field(description="Repo-relative file path.")
    content_sha256: str = Field(description="SHA-256 of the file bytes (content address).")
    summary: dict = Field(
        default_factory=dict, description="Declared counts/totals from the dataset manifest."
    )


class ModelVersion(BaseModel):
    """One model/forecast layer that participated, pinned to its code (SPEC §33)."""

    id: str
    name: str
    spec_sections: list[str] = Field(default_factory=list)
    code: str = Field(description="Python module path implementing the model.")
    determinism: str = Field(description="'deterministic' | 'stochastic (seeded)'.")
    output_tag: MetricTag = Field(description="Provenance tag of this model's numbers.")
    llm_touches_numbers: bool = Field(
        default=False, description="MUST be False for numeric models (SPEC §34)."
    )


class ReproManifest(BaseModel):
    """The complete reproducibility record for one run (SPEC §32)."""

    provenance: MetricTag = Field(
        MetricTag.observed,
        description="The manifest pins inputs/code; it is Observed about the run.",
    )
    note: str = Field(
        default=(
            "Reproducibility manifest (SPEC §32). Captures dataset versions, model "
            "versions, parameters, seed, policy DSL, assumptions, code version and "
            "timestamp. The run_id is a content hash of the reproducing inputs "
            "(timestamp excluded), so identical inputs always yield the same run_id "
            "— that is the REPRODUCE RUN key. Deterministic, no LLM (SPEC §32/§34)."
        )
    )

    # --- the reproduction key ------------------------------------------------
    run_id: str = Field(
        description="SHA-256 content address of the reproducing inputs (stable across runs)."
    )
    reproducible: bool = Field(
        description="True when re-executing the deterministic core yields an identical digest."
    )
    output_digest: str = Field(
        description="SHA-256 of the canonical simulation outputs for this run."
    )

    # --- SPEC §32 required record --------------------------------------------
    created_at: str = Field(
        description="ISO-8601 server timestamp. Metadata only — excluded from run_id."
    )
    app_version: str
    code_version: str = Field(
        description="Git commit of the running code, or a documented fallback."
    )
    seed: int | None = Field(
        default=None, description="Random seed (the deterministic core ignores it, echoed for §32)."
    )
    policy: PolicyDSL = Field(description="The exact compiled Policy DSL that was run.")
    shocks: dict = Field(default_factory=dict, description="Exogenous shocks applied, if any.")

    datasets: list[DatasetVersion] = Field(default_factory=list)
    models: list[ModelVersion] = Field(default_factory=list)
    assumptions: list[AssumptionRecord] = Field(
        default_factory=list,
        description="Every documented numeric assumption in force (read live from code).",
    )
    prompts: list[dict] = Field(
        default_factory=list,
        description="LLM prompts that entered the numeric path — always empty (SPEC §34).",
    )

    inputs_fingerprint: dict = Field(
        default_factory=dict,
        description="The exact components hashed into run_id, for audit.",
    )
    how_to_reproduce: str = Field(
        default="",
        description="Human-readable instructions to regenerate the identical run.",
    )
