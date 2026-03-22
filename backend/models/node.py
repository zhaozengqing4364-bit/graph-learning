"""Node models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class NodeCreate(BaseModel):
    node_id: str | None = None
    name: str = Field(max_length=500)
    summary: str = Field(default="", max_length=50000)
    why_it_matters: str = Field(default="", max_length=50000)
    article_body: str = Field(default="", max_length=500000)
    importance: int = Field(default=3, ge=1, le=5)
    status: str = Field(default="unseen", pattern="^(unseen|browsed|learning|practiced|review_due|mastered)$")


class NodeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=50000)
    why_it_matters: str | None = Field(default=None, max_length=50000)
    article_body: str | None = Field(default=None, max_length=500000)
    importance: int | None = Field(default=None, ge=1, le=5)
    status: str | None = Field(default=None, pattern="^(unseen|browsed|learning|practiced|review_due|mastered)$")


class Node(BaseModel):
    node_id: str
    name: str
    summary: str = ""
    why_it_matters: str = ""
    article_body: str = ""
    applications: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    importance: int = 3
    status: str = "unseen"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    topic_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(cls, data: NodeCreate, topic_id: str = "") -> Node:
        return cls(
            node_id=data.node_id or generate_id("nd"),
            name=data.name,
            summary=data.summary,
            why_it_matters=data.why_it_matters,
            article_body=data.article_body,
            importance=data.importance,
            status=data.status,
            topic_id=topic_id,
        )


class NodeNeighbor(BaseModel):
    node_id: str
    name: str
    relation_type: str = ""
    summary: str = ""


class NodeDetail(BaseModel):
    node: Node
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    concept_refs: list[str] = Field(default_factory=list)
    prerequisites: list[NodeNeighbor] = Field(default_factory=list)
    contrasts: list[NodeNeighbor] = Field(default_factory=list)
    applications: list[NodeNeighbor] = Field(default_factory=list)
    misunderstandings: list[NodeNeighbor] = Field(default_factory=list)
    related: list[NodeNeighbor] = Field(default_factory=list)
    ability: dict | None = None
    why_now: str = ""


class ExpandRequest(BaseModel):
    depth_limit: int = Field(default=1, ge=1, le=5)
    strategy: str = Field(default="balanced", pattern="^(mainline_first|balanced|deep_dive)$")
    session_id: str | None = None
    intent: str | None = None


class DeferRequest(BaseModel):
    source_node_id: str | None = None
    reason: str = ""


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(unseen|browsed|learning|practiced|review_due|mastered)$")


class ExportRequest(BaseModel):
    export_type: str = Field(default="markdown", pattern="^(markdown|json|anki)$")
