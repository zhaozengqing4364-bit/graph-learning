"""Session models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class SessionCreate(BaseModel):
    entry_node_id: str | None = None


class SessionVisit(BaseModel):
    node_id: str
    action_type: str = Field(default="open_node", pattern=r"^(open_node|practice|expand)$")


class Session(BaseModel):
    session_id: str
    topic_id: str
    entry_node_id: str | None = None
    status: str = Field(default="active", pattern=r"^(active|completed)$")
    visited_node_ids: list[str] = Field(default_factory=list)
    practice_count: int = 0
    started_at: str = ""
    completed_at: str | None = None
    summary: str | None = None

    @classmethod
    def create(cls, topic_id: str, data: SessionCreate) -> Session:
        now = datetime.now().isoformat()
        return cls(
            session_id=generate_id("ss"),
            topic_id=topic_id,
            entry_node_id=data.entry_node_id,
            status="active",
            started_at=now,
        )
