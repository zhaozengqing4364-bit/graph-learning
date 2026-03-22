"""Misconception models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class MisconceptionRecord(BaseModel):
    """A misconception linked to a concept node."""
    misconception_id: str
    concept_node_id: str
    description: str = Field(default="", max_length=50000)
    severity: int = 1
    correction: str = Field(default="", max_length=50000)
    topic_id: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""

    @classmethod
    def create(
        cls,
        concept_node_id: str,
        description: str = "",
        severity: int = 1,
        correction: str = "",
        topic_id: str = "",
        tags: list[str] | None = None,
    ) -> MisconceptionRecord:
        return cls(
            misconception_id=generate_id("mc"),
            concept_node_id=concept_node_id,
            description=description,
            severity=severity,
            correction=correction,
            topic_id=topic_id,
            tags=tags or [],
        )
