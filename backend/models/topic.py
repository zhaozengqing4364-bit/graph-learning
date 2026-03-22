"""Topic models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class TopicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source_type: str = Field(default="concept", pattern="^(concept|question|article|notes|mixed)$")
    source_content: str = Field(default="", max_length=500000)
    learning_intent: str = Field(default="build_system", pattern="^(fix_gap|build_system|solve_task|prepare_expression|prepare_interview)$")
    mode: str = Field(default="full_system", pattern="^(shortest_path|full_system)$")


class TopicUpdate(BaseModel):
    title: str | None = None
    learning_intent: str | None = None
    mode: str | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|archived)$")


class Topic(BaseModel):
    topic_id: str
    title: str
    source_type: str
    source_content: str = ""
    learning_intent: str = "build_system"
    mode: str = "full_system"
    status: str = "active"
    current_node_id: str | None = None
    last_session_id: str | None = None
    total_nodes: int = 0
    learned_nodes: int = 0
    total_practice: int = 0
    total_sessions: int = 0
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(cls, data: TopicCreate) -> Topic:
        now = datetime.now().isoformat()
        return cls(
            topic_id=generate_id("tp"),
            title=data.title,
            source_type=data.source_type,
            source_content=data.source_content,
            learning_intent=data.learning_intent,
            mode=data.mode,
            status="active",
            created_at=now,
            updated_at=now,
        )
