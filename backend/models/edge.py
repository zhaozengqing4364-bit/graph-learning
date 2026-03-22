"""Edge models and relation type enum."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class EdgeType(str, Enum):
    PREREQUISITE = "PREREQUISITE"
    CONTRASTS = "CONTRASTS"
    VARIANT_OF = "VARIANT_OF"
    APPLIES_IN = "APPLIES_IN"
    EXTENDS = "EXTENDS"
    MISUNDERSTOOD_AS = "MISUNDERSTOOD_AS"


class Edge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str = Field(pattern=r"^(PREREQUISITE|CONTRASTS|VARIANT_OF|APPLIES_IN|EXTENDS|MISUNDERSTOOD_AS)$")
    reason: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = ""

    @classmethod
    def create(
        cls,
        source_node_id: str,
        target_node_id: str,
        relation_type: str,
        reason: str = "",
    ) -> Edge:
        return cls(
            edge_id=generate_id("eg"),
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            reason=reason,
        )


class EdgeCreate(BaseModel):
    source_node_id: str
    target_node_id: str
    relation_type: str = Field(pattern=r"^(PREREQUISITE|CONTRASTS|VARIANT_OF|APPLIES_IN|EXTENDS|MISUNDERSTOOD_AS)$")
    reason: str = ""
