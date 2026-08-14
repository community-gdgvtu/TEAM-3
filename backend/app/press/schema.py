"""Pydantic schemas for the press conference simulation (SPEC §16)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag

SIMULATED_LABEL = "SIMULATED — fictional press conference, not a real event or outlet"


class ReporterArchetype(str, Enum):
    """The editorial lens a questioner brings (mirrors the media archetypes)."""

    public_broadcaster = "public_broadcaster"
    business_press = "business_press"
    tabloid = "tabloid"
    environmental = "environmental"
    opposition_local = "opposition_local"


class PressQuestion(BaseModel):
    """One journalist's pointed, evidence-anchored question."""

    archetype: ReporterArchetype
    outlet_label: str = Field(description="Fictional outlet (never a real name).")
    reporter: str = Field(description="Fictional reporter role, e.g. 'Business correspondent'.")
    question: str
    angle: str = Field(description="The lens / line of attack.")
    hostility: str = Field(description="'friendly' | 'neutral' | 'hostile'.")
    cited_refs: list[str] = Field(
        default_factory=list, description="Metric keys / event ids the question is grounded in."
    )


class PressAnswer(BaseModel):
    """The spokesperson's grounded response to one question."""

    stance: str = Field(description="'defends' | 'acknowledges' | 'rebuts' | 'commits'.")
    answer: str
    cited_refs: list[str] = Field(
        default_factory=list, description="Metric keys / event ids cited in the answer."
    )


class PressExchange(BaseModel):
    """A question and its answer."""

    question: PressQuestion
    answer: PressAnswer


class PressConference(BaseModel):
    """A full simulated press conference at one horizon (SPEC §16)."""

    provenance: MetricTag = Field(
        MetricTag.generated,
        description="Prose is Generated over Simulated figures; no LLM invents a number.",
    )
    disclaimer: str = Field(default=SIMULATED_LABEL)
    note: str = Field(
        default=(
            "Simulated press conference: questions and answers are built from the "
            "deterministic simulation's Δ metrics, event ledger and cohort opinion. "
            "Every figure is copied from the model; an LLM may polish prose but never "
            "produces a number (SPEC §16/§34). Fictional outlets and reporters only."
        )
    )
    policy_id: str
    method: str = Field(default="template", description="'llm' or 'template'.")
    horizon: Checkpoint = Field(description="When the conference is held.")
    spokesperson: str = Field(default="Government transport spokesperson")
    opening_statement: str
    opening_refs: list[str] = Field(default_factory=list)
    exchanges: list[PressExchange] = Field(default_factory=list)
    public_mood: str = Field(description="One-line read of the room from opinion state.")
