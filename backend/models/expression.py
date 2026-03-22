"""Expression asset models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class ExpressionAssetCreate(BaseModel):
    attempt_id: str | None = None
    expression_type: str = Field(pattern=r"^(define|example|contrast|apply|teach_beginner|compress|explain)$")
    user_expression: str = Field(max_length=50000)
    ai_rewrite: str = Field(default="", max_length=50000)
    skeleton: str = Field(default="", max_length=50000)
    quality_tags: list[str] = Field(default_factory=list)


class ExpressionAsset(BaseModel):
    asset_id: str
    topic_id: str
    node_id: str
    session_id: str | None = None
    expression_type: str = Field(pattern=r"^(define|example|contrast|apply|teach_beginner|compress|explain)$")
    user_expression: str
    ai_rewrite: str = ""
    skeleton: str = ""
    quality_tags: list[str] = Field(default_factory=list)
    favorited: bool = False
    created_at: str = ""

    @classmethod
    def create(
        cls,
        topic_id: str,
        node_id: str,
        data: ExpressionAssetCreate,
        session_id: str | None = None,
    ) -> ExpressionAsset:
        now = datetime.now().isoformat()
        return cls(
            asset_id=generate_id("ea"),
            topic_id=topic_id,
            node_id=node_id,
            session_id=session_id,
            expression_type=data.expression_type,
            user_expression=data.user_expression,
            ai_rewrite=data.ai_rewrite,
            skeleton=data.skeleton,
            quality_tags=data.quality_tags,
            created_at=now,
        )
