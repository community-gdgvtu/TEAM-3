"""Pydantic schemas for the service capability manifest.

The manifest is a transparency artifact describing the HTTP surface, so it is
Observed about the service — nothing here is a simulation output. Per-endpoint
``output_tag`` records the provenance class of *that endpoint's* numbers (or
``None`` for prose-only / mixed / pure-metadata routes); the field is
deliberately **not** named ``provenance`` so the whole-surface §34 provenance
walk only enforces the top-level ``provenance`` tag, not this descriptive echo.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..baseline.schema import MetricTag


class EndpointCard(BaseModel):
    """A self-describing entry for one HTTP route."""

    path: str = Field(description="Route path, e.g. '/simulate'.")
    methods: list[str] = Field(description="HTTP methods served, e.g. ['POST'].")
    area: str = Field(description="Functional area this route belongs to.")
    spec_sections: list[str] = Field(
        default_factory=list, description="SPEC sections this route implements."
    )
    summary: str = Field(description="One-line description of what the route returns.")
    needs_body: bool = Field(
        description="Whether a request body is required (true for the POST endpoints)."
    )
    keyless_example: Optional[str] = Field(
        default=None,
        description="Companion GET that returns a canonical result with no body, if any.",
    )
    produces_numbers: bool = Field(
        default=False,
        description="Whether this route emits core numeric effects (vs prose/metadata).",
    )
    output_tag: Optional[MetricTag] = Field(
        default=None,
        description=(
            "Provenance class of this route's numbers (None = prose-only, mixed, "
            "or pure transparency metadata)."
        ),
    )


class CapabilityGroup(BaseModel):
    """A functional area grouping several endpoints."""

    area: str
    spec_sections: list[str] = Field(default_factory=list)
    summary: str = Field(description="What this area of the engine does.")
    endpoints: list[EndpointCard] = Field(default_factory=list)


class CapabilityManifest(BaseModel):
    """The full self-describing catalogue of the engine's HTTP surface."""

    provenance: MetricTag = Field(
        MetricTag.observed,
        description="The manifest describes the service, so it is Observed about itself.",
    )
    note: str = Field(
        default=(
            "Service capability manifest: every HTTP route mapped to its SPEC "
            "section, functional area, provenance class and keyless-example "
            "companion, reconciled live against the running app's routes so it "
            "cannot drift. Where /registry catalogues the models and /data-fabric "
            "the datasets, this catalogues the HTTP surface itself. Transparency "
            "artifact, not a simulation output; no LLM (SPEC §34)."
        )
    )
    app_version: str
    generated_from: str = Field(
        default="live route introspection reconciled with a curated catalogue",
        description="How the surface was enumerated (not hand-copied).",
    )
    groups: list[CapabilityGroup] = Field(default_factory=list)
    keyless_examples: list[str] = Field(
        default_factory=list,
        description="Every GET that returns a canonical answer with no request body.",
    )
    undocumented_routes: list[str] = Field(
        default_factory=list,
        description=(
            "Live API routes with no catalogue card — MUST be empty; surfaced "
            "(not hidden) so a new route without a description fails the guard."
        ),
    )
    phantom_cards: list[str] = Field(
        default_factory=list,
        description="Catalogue cards for routes that no longer exist — MUST be empty.",
    )
    counts: dict = Field(
        default_factory=dict,
        description="Summary counts (routes, areas, GET/POST, keyless examples).",
    )
