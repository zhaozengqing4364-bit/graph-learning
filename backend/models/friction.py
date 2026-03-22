"""Friction record models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class FrictionType:
    PREREQUISITE_GAP = "prerequisite_gap"
    CONCEPT_CONFUSION = "concept_confusion"
    LACK_OF_EXAMPLE = "lack_of_example"
    WEAK_STRUCTURE = "weak_structure"
    ABSTRACT_OVERLOAD = "abstract_overload"
    WEAK_RECALL = "weak_recall"
    WEAK_APPLICATION = "weak_application"

    ALL: frozenset[str] = frozenset({
        PREREQUISITE_GAP, CONCEPT_CONFUSION, LACK_OF_EXAMPLE,
        WEAK_STRUCTURE, ABSTRACT_OVERLOAD, WEAK_RECALL, WEAK_APPLICATION,
    })


class FrictionRecord(BaseModel):
    friction_id: str
    topic_id: str
    node_id: str
    session_id: str | None = None
    friction_type: str
    severity: int = Field(default=1, ge=1, le=5)
    evidence_text: str = Field(default="", max_length=50000)
    suggested_next_node_id: str | None = None
    description: str = Field(default="", max_length=50000)
    tags: list[str] = []
    resolved_at: str = ""
    created_at: str = ""

    @classmethod
    def create(
        cls,
        topic_id: str,
        node_id: str,
        friction_type: str,
        severity: int = 1,
        evidence_text: str = "",
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> FrictionRecord:
        import logging
        if friction_type not in FrictionType.ALL:
            logging.getLogger(__name__).warning(
                "Rejected unknown friction_type '%s', using 'weak_structure' instead",
                friction_type,
            )
            friction_type = "weak_structure"
        now = datetime.now().isoformat()
        return cls(
            friction_id=generate_id("fr"),
            topic_id=topic_id,
            node_id=node_id,
            session_id=session_id,
            friction_type=friction_type,
            severity=severity,
            evidence_text=evidence_text,
            description=friction_type.replace("_", " "),
            tags=tags or [friction_type],
            created_at=now,
        )
