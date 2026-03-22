"""Ability record and snapshot models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.models.common import generate_id

# Practice type → primary dimensions affected
PRACTICE_DIMENSION_MAP: dict[str, list[str]] = {
    "define": ["understand", "explain"],
    "example": ["example", "understand"],
    "contrast": ["contrast", "explain"],
    "apply": ["apply", "transfer"],
    "teach_beginner": ["teach", "explain"],
    "compress": ["understand", "recall"],
    "explain": ["explain", "understand"],
    "recall": ["recall", "understand"],
}


class AbilityRecord(BaseModel):
    topic_id: str
    node_id: str
    understand: int = 0
    example: int = 0
    contrast: int = 0
    apply: int = 0
    explain: int = 0
    recall: int = 0
    transfer: int = 0
    teach: int = 0
    recall_confidence: float = 1.0
    last_reviewed_at: str = ""
    review_history_count: int = 0
    updated_at: str = ""


class AbilityDelta(BaseModel):
    understand: int = 0
    example: int = 0
    contrast: int = 0
    apply: int = 0
    explain: int = 0
    recall: int = 0
    transfer: int = 0
    teach: int = 0


class AbilitySnapshot(BaseModel):
    ability_snapshot_id: str
    topic_id: str
    node_id: str
    session_id: str | None = None
    understand: int = 0
    example: int = 0
    contrast: int = 0
    apply: int = 0
    explain: int = 0
    recall: int = 0
    transfer: int = 0
    teach: int = 0
    source: str = "practice"
    created_at: str = ""

    @classmethod
    def create(
        cls,
        topic_id: str,
        node_id: str,
        record: AbilityRecord,
        source: str = "practice",
        session_id: str | None = None,
    ) -> AbilitySnapshot:
        now = datetime.now().isoformat()
        return cls(
            ability_snapshot_id=generate_id("ab"),
            topic_id=topic_id,
            node_id=node_id,
            session_id=session_id,
            understand=record.understand,
            example=record.example,
            contrast=record.contrast,
            apply=record.apply,
            explain=record.explain,
            recall=record.recall,
            transfer=record.transfer,
            teach=record.teach,
            source=source,
            created_at=now,
        )


def apply_delta(record: AbilityRecord, delta: AbilityDelta) -> AbilityRecord:
    """Apply ability delta to a record, respecting update rules with adaptive scaling.

    Adaptive scaling: lower ability values get more headroom for growth,
    higher values get tighter increments to reflect mastery plateau.
    """
    from datetime import datetime
    now = datetime.now().isoformat()

    def adaptive_clamp(val: int, increment: int) -> int:
        # Scale max increment based on current level (adaptive growth curve)
        if val < 30:
            max_inc = 15  # Beginner: allow larger gains
        elif val < 70:
            max_inc = 10  # Intermediate: standard
        else:
            max_inc = 5   # Advanced: diminishing returns
        max_dec = -5
        increment = max(max_dec, min(max_inc, increment))
        return max(0, min(100, val + increment))

    return AbilityRecord(
        topic_id=record.topic_id,
        node_id=record.node_id,
        understand=adaptive_clamp(record.understand, delta.understand),
        example=adaptive_clamp(record.example, delta.example),
        contrast=adaptive_clamp(record.contrast, delta.contrast),
        apply=adaptive_clamp(record.apply, delta.apply),
        explain=adaptive_clamp(record.explain, delta.explain),
        recall=adaptive_clamp(record.recall, delta.recall),
        transfer=adaptive_clamp(record.transfer, delta.transfer),
        teach=adaptive_clamp(record.teach, delta.teach),
        recall_confidence=record.recall_confidence,
        last_reviewed_at=record.last_reviewed_at,
        review_history_count=record.review_history_count,
        updated_at=now,
    )
