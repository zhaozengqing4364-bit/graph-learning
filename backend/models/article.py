"""Article workspace models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class SourceArticleCreate(BaseModel):
    title: str = Field(max_length=500)
    body: str = Field(default="", max_length=500000)


class SourceArticleUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, max_length=500000)


class SourceArticle(BaseModel):
    article_id: str
    topic_id: str
    title: str
    body: str = ""
    article_kind: str = "source"
    source_label: str = "我的文章"
    is_editable: bool = True
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(cls, topic_id: str, data: SourceArticleCreate) -> "SourceArticle":
        now = datetime.now().isoformat()
        return cls(
            article_id=f"source:{generate_id('ar')}",
            topic_id=topic_id,
            title=data.title,
            body=data.body,
            article_kind="source",
            source_label="我的文章",
            is_editable=True,
            created_at=now,
            updated_at=now,
        )


class ConceptNoteUpsert(BaseModel):
    title: str
    body: str = ""


class ConceptNote(BaseModel):
    note_id: str
    topic_id: str
    concept_key: str
    title: str
    body: str = ""
    updated_at: str = ""


class ReadingTrailEntry(BaseModel):
    article_id: str
    title: str


class ReadingStateUpsert(BaseModel):
    article_id: str
    scroll_top: float = 0
    trail: list[ReadingTrailEntry] = Field(default_factory=list)
    completed_article_ids: list[str] = Field(default_factory=list)


class ReadingState(BaseModel):
    topic_id: str
    article_id: str
    scroll_top: float = 0
    trail: list[ReadingTrailEntry] = Field(default_factory=list)
    completed_article_ids: list[str] = Field(default_factory=list)
    updated_at: str = ""


class ConceptCandidateCreate(BaseModel):
    concept_text: str
    source_article_id: str | None = None
    paragraph_index: int | None = None
    anchor_id: str | None = None
    origin: str = Field(default="manual", pattern="^(manual|article_analysis)$")


class ConceptCandidateConfirm(BaseModel):
    concept_name: str | None = None


class ConceptCandidate(BaseModel):
    candidate_id: str
    topic_id: str
    concept_text: str
    normalized_text: str
    status: str = Field(default="candidate", pattern="^(candidate|confirmed|ignored)$")
    matched_node_id: str | None = None
    matched_concept_name: str = ""
    source_article_id: str | None = None
    paragraph_index: int | None = None
    anchor_id: str = ""
    origin: str = "manual"
    confidence: float = 0
    created_at: str = ""
    updated_at: str = ""


class WorkspaceSearchResult(BaseModel):
    articles: list[dict] = Field(default_factory=list)
    concepts: list[dict] = Field(default_factory=list)
    notes: list[dict] = Field(default_factory=list)
