"""Review item models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class ReviewItemCreate(BaseModel):
    node_id: str
    review_type: str = Field(default="recall", pattern=r"^(recall|contrast|explain|spaced)$")
    priority: float = 0.0
    due_at: str | None = None
    reason: str = ""



class ReviewSubmitRequest(BaseModel):
    user_answer: str = Field(min_length=5, max_length=50000)
    session_id: str | None = None


class ReviewItem(BaseModel):
    review_id: str
    topic_id: str
    node_id: str
    review_type: str = Field(default="recall", pattern=r"^(recall|contrast|explain|spaced)$")
    priority: float = 0.0
    status: str = Field(default="pending", pattern=r"^(pending|due|completed|failed|skipped|snoozed|cancelled)$")
    due_at: str | None = None
    next_review_at: str | None = None
    last_result: str | None = None
    reason: str = ""
    history_count: int = 0
    created_at: str = ""
    completed_at: str | None = None

    @classmethod
    def create(
        cls,
        topic_id: str,
        data: ReviewItemCreate,
    ) -> ReviewItem:
        now = datetime.now().isoformat()
        return cls(
            review_id=generate_id("rv"),
            topic_id=topic_id,
            node_id=data.node_id,
            review_type=data.review_type,
            priority=data.priority,
            due_at=data.due_at or now,
            reason=data.reason,
            status="pending",
            created_at=now,
        )


class ReviewFeedbackDetail(BaseModel):
    correctness: str = "medium"
    clarity: str = "medium"
    naturalness: str = "medium"
    issues: list[str] = []
    suggestions: list[str] = []


class ReviewResult(BaseModel):
    result: str = "medium"  # FeedbackLevel: good/medium/weak
    feedback: ReviewFeedbackDetail | dict = {}
    ability_update: dict | None = None
    next_due_time: str | None = None
    needs_relearn: bool = False
