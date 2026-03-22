"""Practice models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.common import generate_id


class PracticeType:
    DEFINE = "define"
    EXAMPLE = "example"
    CONTRAST = "contrast"
    APPLY = "apply"
    TEACH_BEGINNER = "teach_beginner"
    COMPRESS = "compress"


class PracticeRequest(BaseModel):
    practice_type: str = Field(default="define", pattern="^(define|example|contrast|apply|teach_beginner|compress|explain)$")
    difficulty: str = Field(default="adaptive", pattern="^(easy|medium|hard|adaptive)$")
    regenerate: bool = False


class PracticePrompt(BaseModel):
    practice_type: str
    prompt_text: str
    minimum_answer_hint: str = ""
    evaluation_dimensions: list[str] = Field(default_factory=list)


class PracticeSubmit(BaseModel):
    session_id: str | None = None
    practice_type: str = Field(pattern="^(define|example|contrast|apply|teach_beginner|compress|explain)$")
    prompt_text: str = Field(max_length=50000)
    user_answer: str = Field(min_length=5, max_length=50000)


class PracticeFeedback(BaseModel):
    correctness: str = ""
    clarity: str = ""
    naturalness: str = ""
    consistency: str = ""
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    recommended_answer: str = ""
    expression_skeleton: str = ""
    follow_up_question: str = ""


class PracticeAttempt(BaseModel):
    attempt_id: str
    topic_id: str
    node_id: str
    session_id: str | None = None
    practice_type: str
    prompt_text: str = ""
    user_answer: str
    feedback: str | None = None
    scores: dict | None = None
    created_at: str = ""

    @classmethod
    def create(
        cls,
        topic_id: str,
        node_id: str,
        practice_type: str,
        user_answer: str,
        session_id: str | None = None,
        prompt_text: str = "",
    ) -> PracticeAttempt:
        return cls(
            attempt_id=generate_id("pa"),
            topic_id=topic_id,
            node_id=node_id,
            session_id=session_id,
            practice_type=practice_type,
            prompt_text=prompt_text,
            user_answer=user_answer,
        )


class PracticeResult(BaseModel):
    attempt_id: str
    feedback: PracticeFeedback | None = None
    recommended_answer: str = ""
    expression_skeleton: str = ""
    ability_update: dict | None = None
    friction_tags: list[str] = Field(default_factory=list)
    diagnosis_fallback: bool = False
    next_practice_recommendation: list[str] = Field(default_factory=list)
